"""Clearly marked synthetic data for an offline integration test, never thesis evidence."""
import json
import numpy as np
from .recording import create_recording, finalize


def simulate(directory, config, metadata, seconds=12, seed=7, gap=None):
    rate = config['radio']['nominal_rate_hz']
    if seconds < config['preprocessing']['long_seconds'] + 1:
        raise ValueError('Simulation must exceed the long-window duration')
    meta = {**metadata, 'consent_confirmed': True}
    folder = create_recording(directory, config, meta, synthetic=True)
    rng = np.random.default_rng(seed)
    with (folder / 'raw.ndjson').open('x', encoding='utf-8') as stream:
        for seq in range(int(seconds * rate)):
            tx_us = 1_000_000 + round(seq * 1e6 / rate)
            common = {'v': 1, 'app_seq': seq, 'tx_us': tx_us, 'tx_boot_id': 99}
            stream.write(json.dumps({**common, 'kind': 'TX', 'device_id': 'tx',
                         'boot_id': 99, 'send_status': 0}) + '\n')
            if gap and gap[0] <= seq/rate < gap[1]:
                continue
            for link_index, link in enumerate(('rx-a', 'rx-b')):
                local_us = tx_us + (link_index+1)*12345
                identity = {'v': 1, 'device_id': link, 'boot_id': link_index+101,
                            'device_us': local_us}
                amplitude = 30 + 4*np.sin(2*np.pi*0.8*seq/rate) + link_index*2
                values = np.round(amplitude + rng.normal(0, 1, (64, 2))).astype(int)
                row = {**identity, 'kind': 'CSI', 'len': 128, 'iq': values.ravel().tolist(),
                       'first_word_invalid': seq % 3 == 0, 'queue_drops': 0,
                       'rx_seq': seq % 4096, 'channel': config['radio']['channel'],
                       'sig_mode': 1, 'mcs': 0, 'cwb': 0, 'rx_state': 0,
                       'rssi_dbm': -45, 'noise_floor_dbm': None, 'format': 'lltf_only_v1'}
                marker = {**common, **identity, 'kind': 'MARKER'}
                # Deliberately vary callback order; matching must be by identity.
                for event in ((row, marker) if seq % 2 else (marker, row)):
                    stream.write(json.dumps(event) + '\n')
    finalize(folder, 'complete', {'synthetic': True, 'seed': seed})
    return folder
