"""Packet-identity alignment and acquisition quality checks."""
from collections import Counter, defaultdict
from pathlib import Path
import hashlib
import numpy as np
from .protocol import parse_line, load_json, validate_config


def iq_amplitude(row):
    """Keep original pair indices; invalid first four bytes become NaN."""
    values = np.asarray(row['iq'], dtype=np.float64).reshape(-1, 2)
    amplitude = np.hypot(values[:, 1], values[:, 0])  # imaginary, then real
    if row['first_word_invalid']:
        amplitude[:2] = np.nan
    return amplitude


def align_recording(directory, *, allow_empty=False):
    folder = Path(directory)
    for name, expected in load_json(folder / 'checksums.json').items():
        if Path(name).name != name:
            raise ValueError('Unsafe checksum filename')
        if hashlib.sha256((folder/name).read_bytes()).hexdigest() != expected:
            raise ValueError('Recording checksum mismatch: ' + name)
    config = validate_config(load_json(folder / 'config.json'))
    meta = load_json(folder / 'metadata.json')
    if meta['state'] != 'complete':
        raise ValueError('Only complete recordings may be processed')
    markers, csi, transmitted = defaultdict(list), defaultdict(list), {}
    reasons = Counter()
    boots = defaultdict(set)
    drops = Counter()
    counts = {link: Counter() for link in ('rx-a', 'rx-b')}
    with (folder / 'raw.ndjson').open(encoding='utf-8') as stream:
        for line in stream:
            try:
                row = parse_line(line)
            except (ValueError, UnicodeError):
                reasons['malformed_records'] += 1
                continue
            if row is None:
                continue
            device = row['device_id']
            boots[device].add(row['boot_id'])
            if row['kind'] == 'TX' and row['send_status'] == 0:
                key = (row['tx_boot_id'], row['app_seq'])
                if key in transmitted:
                    raise ValueError('Duplicate TX identity')
                transmitted[key] = row['tx_us']
            if row['kind'] in ('CSI', 'MARKER'):
                key = (device, row['boot_id'], row['device_us'])
                (markers if row['kind'] == 'MARKER' else csi)[key].append(row)
                counts[device][row['kind']] += 1
                if row['kind'] == 'CSI' and not any(row['iq'][4 if row['first_word_invalid'] else 0:]):
                    counts[device]['all_zero_iq'] += 1
    if any(len(values) > 1 for values in boots.values()):
        raise ValueError('A board rebooted during the recording; start a new recording')
    by_link = {name: {} for name in ('rx-a', 'rx-b')}
    for key, candidates in csi.items():
        for sample in candidates:
            drops[sample['device_id']] = max(drops[sample['device_id']], sample['queue_drops'])
        marker = markers.get(key, [])
        if len(candidates) != 1 or len(marker) != 1:
            reasons['missing_or_ambiguous_marker'] += len(candidates)
            continue
        row, mark = candidates[0], marker[0]
        counts[row['device_id']]['timestamp_pairs'] += 1
        expected = (row['len'] == 128 and row.get('format') == 'lltf_only_v1'
                    and row['channel'] == config['radio']['channel']
                    and row['sig_mode'] == 1 and row['mcs'] == 0
                    and row['cwb'] == 0 and row['rx_state'] == 0)
        if not expected:
            reasons['unexpected_radio_or_csi_format'] += 1
            continue
        packet = (mark['tx_boot_id'], mark['app_seq'])
        if packet in by_link[row['device_id']]:
            raise ValueError('Duplicate application sequence on one receiver')
        values = iq_amplitude(row)[config['preprocessing']['raw_pair_indices']]
        if not np.isfinite(values).all():
            reasons['invalid_selected_subcarrier'] += 1
            continue
        by_link[row['device_id']][packet] = (mark['tx_us'], values)
    common = sorted(set(by_link['rx-a']) & set(by_link['rx-b']),
                    key=lambda key: by_link['rx-a'][key][0])
    if not common and not allow_empty:
        raise ValueError('No unambiguous shared TX packets across both receivers')
    if len({key[0] for key in common}) > 1:
        raise ValueError('Transmitter reboot detected')
    times, data = [], []
    for key in common:
        a, b = by_link['rx-a'][key], by_link['rx-b'][key]
        if a[0] != b[0] or (key in transmitted and transmitted[key] != a[0]):
            raise ValueError('Shared packet has inconsistent transmitter timestamps')
        times.append(a[0] / 1e6)
        data.append(np.stack([a[1], b[1]]))
    times = np.asarray(times)
    if np.any(np.diff(times) <= 0):
        raise ValueError('Non-increasing TX timestamps')
    accepted = set(transmitted)
    report = {'synthetic': meta['synthetic'], 'shared_packets': len(common),
              'largest_shared_tx_gap_ms': float(np.diff(times).max() * 1000) if len(times) > 1 else None,
              'links': {link: {'csi': counts[link]['CSI'], 'markers': counts[link]['MARKER'],
                              'timestamp_pairs': counts[link]['timestamp_pairs'],
                              'accepted_pairs': len(by_link[link]),
                              'all_zero_iq': counts[link]['all_zero_iq']} for link in counts},
              'rejected': dict(reasons),
              'device_queue_drops': dict(drops),
              'accepted_send_denominator': len(accepted) or None,
              'delivery_against_accepted_sends': {
                  link: len(set(rows) & accepted) / len(accepted) if accepted else None
                  for link, rows in by_link.items()},
              'note': 'Denominator is API-accepted sends captured on TX, not proof of over-air transmission.',
              'alignment': 'exact TX boot/application sequence, joined to CSI by RX boot/local timestamp'}
    values = np.asarray(data).reshape(len(common), 2, len(config['preprocessing']['raw_pair_indices']))
    return times, values, config, meta, report
