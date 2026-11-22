"""Immutable recording folders and bounded, concurrent serial capture."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import importlib.metadata
import json
import queue
import subprocess
import sys
import threading
import time
from .protocol import parse_line, validate_config, validate_metadata


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def create_recording(directory, config, metadata, synthetic=False):
    validate_config(config)
    validate_metadata(metadata)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    write_json(directory / 'config.json', config)
    write_json(directory / 'metadata.json', {**metadata, 'synthetic': synthetic,
               'started_at_utc': datetime.now(timezone.utc).isoformat(),
               'state': 'recording'})
    try:
        version = subprocess.check_output(['git', '-C', str(Path(__file__).resolve().parents[3]),
                                            'rev-parse', 'HEAD'], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        version = None
    try:
        dirty = bool(subprocess.check_output(['git', '-C', str(Path(__file__).resolve().parents[3]),
                     'status', '--porcelain'], stderr=subprocess.DEVNULL).strip())
    except (OSError, subprocess.CalledProcessError):
        dirty = None
    write_json(directory / 'provenance.json', {'tools_version': '0.1.0', 'git_commit': version,
               'working_tree_dirty': dirty, 'python_version': sys.version.split()[0],
               'numpy_version': importlib.metadata.version('numpy'),
               'note': 'Git commit identifies source checkout, not proof of flashed firmware. Record flash build separately.'})
    return directory


def finalize(directory, state, stats):
    directory = Path(directory)
    meta = json.loads((directory / 'metadata.json').read_text())
    meta.update(state=state, finished_at_utc=datetime.now(timezone.utc).isoformat())
    write_json(directory / 'metadata.json', meta)
    write_json(directory / 'capture_summary.json', stats)
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in directory.iterdir() if p.is_file() and p.name != 'checksums.json'}
    write_json(directory / 'checksums.json', hashes)


def capture(directory, config, metadata, duration):
    """Capture TX and both RX ports. Any serial or host-queue failure aborts."""
    if not 0 < duration <= 3600:
        raise ValueError('Duration must be between zero and 3600 seconds')
    import serial  # Optional live dependency; offline tools do not require it.
    folder = create_recording(directory, config, metadata)
    events = queue.Queue(maxsize=2048)
    stop = threading.Event()
    counters = Counter()
    errors = []
    ports, workers = [], []
    state = 'failed'

    def reader(device, port):
        try:
            with (folder / f"serial-{device['id']}.bin").open('xb') as raw:
                while not stop.is_set():
                    line = port.readline(16384)
                    if not line:
                        continue
                    raw.write(line)
                    try:
                        row = parse_line(line)
                    except (ValueError, UnicodeError):
                        events.put_nowait(('invalid', device['id']))
                        continue
                    if row is not None:
                        if row['device_id'] != device['id']:
                            raise ValueError('Board identity differs from assigned port')
                        row['host_monotonic_ns'] = time.monotonic_ns()
                        events.put_nowait(('record', row))
        except Exception as error:
            errors.append(f"{device['id']}: {type(error).__name__}: {error}")
            stop.set()

    try:
        # Open all ports before starting workers; keep DTR/RTS low to avoid reset.
        for device in config['devices']:
            port = serial.Serial(port=None, baudrate=config['serial_baud'], timeout=0.2)
            ports.append(port)
            port.dtr, port.rts = False, False
            port.port = device['port']
            port.open()
        with (folder / 'raw.ndjson').open('x', encoding='utf-8') as stream:
            for device, port in zip(config['devices'], ports):
                worker = threading.Thread(target=reader, args=(device, port), daemon=True)
                worker.start()
                workers.append(worker)
            deadline = time.monotonic() + duration
            while time.monotonic() < deadline and not stop.is_set():
                try:
                    kind, item = events.get(timeout=0.1)
                except queue.Empty:
                    continue
                if kind == 'record':
                    stream.write(json.dumps(item, separators=(',', ':')) + '\n')
                    counters[item['device_id'] + ':' + item['kind']] += 1
                else:
                    counters[item + ':invalid_lines'] += 1
            stop.set()
            for worker in workers:
                worker.join(timeout=2)
            while not events.empty():
                kind, item = events.get_nowait()
                if kind == 'record':
                    stream.write(json.dumps(item, separators=(',', ':')) + '\n')
                    counters[item['device_id'] + ':' + item['kind']] += 1
                else:
                    counters[item + ':invalid_lines'] += 1
            for identity, kind in [('tx', 'TX'), ('rx-a', 'CSI'), ('rx-b', 'CSI')]:
                if counters[identity + ':' + kind] == 0:
                    errors.append(f'{identity}: no {kind} records received')
            state = 'failed' if errors else 'complete'
    except KeyboardInterrupt:
        state = 'interrupted'
    except Exception as error:
        errors.append(f'host: {type(error).__name__}: {error}')
        raise
    finally:
        stop.set()
        for worker in workers:
            worker.join(timeout=2)
        for port in ports:
            port.close()
        finalize(folder, state, {'counts': dict(counters), 'errors': errors})
    if state != 'complete':
        raise RuntimeError(f'Capture {state}; inspect capture_summary.json')
    return folder
