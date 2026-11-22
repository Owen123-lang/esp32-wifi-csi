"""Versioned firmware NDJSON, preserving the ESP32's raw imaginary/real bytes."""
import json
import math


def integer(value, name, minimum=0, maximum=None):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f'{name} must be an integer')
    if value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f'{name} out of range')
    return value


def parse_line(line):
    """Return None for boot chatter; reject malformed protocol-looking records."""
    if isinstance(line, bytes):
        line = line.decode('utf-8', errors='strict')
    if not line.lstrip().startswith('{'):
        return None
    row = json.loads(line)
    if not isinstance(row, dict) or row.get('v') != 1:
        raise ValueError('Unsupported protocol version')
    kind = row.get('kind')
    if kind not in {'BOOT', 'TX', 'MARKER', 'CSI'}:
        raise ValueError('Unknown record kind')
    if row.get('device_id') not in {'tx', 'rx-a', 'rx-b'}:
        raise ValueError('Unknown device identity')
    integer(row.get('boot_id'), 'boot_id', maximum=2**32-1)
    if kind in {'CSI', 'MARKER'}:
        if row['device_id'] == 'tx':
            raise ValueError('Receiver record on TX device')
        integer(row.get('device_us'), 'device_us', maximum=2**32-1)
    if kind in {'TX', 'MARKER'}:
        integer(row.get('app_seq'), 'app_seq', maximum=2**32-1)
        integer(row.get('tx_boot_id'), 'tx_boot_id', maximum=2**32-1)
        integer(row.get('tx_us'), 'tx_us')
    if kind == 'TX':
        if row['device_id'] != 'tx':
            raise ValueError('TX record on receiver')
        integer(row.get('send_status'), 'send_status')
    if kind == 'CSI':
        data = row.get('iq')
        if not isinstance(data, list) or not data or len(data) % 2:
            raise ValueError('CSI IQ buffer must contain byte pairs')
        if row.get('len') != len(data):
            raise ValueError('CSI length differs from IQ buffer length')
        for value in data:
            integer(value, 'IQ byte', -128, 127)
        if not isinstance(row.get('first_word_invalid'), bool):
            raise ValueError('first_word_invalid must be boolean')
        integer(row.get('queue_drops'), 'queue_drops')
        for name in ('rx_seq', 'channel', 'sig_mode', 'mcs', 'cwb', 'rx_state'):
            integer(row.get(name), name)
        integer(row.get('rssi_dbm'), 'rssi_dbm', -127, 0)
    return row


def load_json(path):
    with open(path, encoding='utf-8') as stream:
        return json.load(stream)


def validate_config(config):
    if config.get('schema_version') != 1:
        raise ValueError('Unsupported experiment config')
    radio = config['radio']
    integer(radio['channel'], 'channel', 1, 11)
    integer(radio['nominal_rate_hz'], 'nominal_rate_hz', 1, 200)
    if radio['bandwidth_mhz'] != 20 or radio['csi_format'] != 'lltf_only_v1':
        raise ValueError('Pilot supports HT20 with LLTF-only CSI')
    devices = config['devices']
    if {d['id'] for d in devices} != {'tx', 'rx-a', 'rx-b'} or len(devices) != 3:
        raise ValueError('Exactly one TX and two distinct RX devices are required')
    for device in devices:
        if device['role'] != ('tx' if device['id'] == 'tx' else 'rx'):
            raise ValueError('Device ID and role disagree')
        if not isinstance(device['port'], str) or not device['port'].strip():
            raise ValueError('Serial port must be a nonempty string')
    integer(config['serial_baud'], 'serial_baud', 9600, 3000000)
    ports = [d['port'] for d in devices]
    if len(set(ports)) != 3:
        raise ValueError('Serial ports must be distinct')
    prep = config['preprocessing']
    bins = prep['raw_pair_indices']
    if not bins or len(set(bins)) != len(bins):
        raise ValueError('Subcarrier buffer indices must be explicit and unique')
    for value in bins:
        integer(value, 'raw_pair_index', 2, 63)
    for name in ('resample_hz', 'short_seconds', 'long_seconds',
                 'stride_seconds', 'max_gap_seconds'):
        value = prep[name]
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f'{name} must be finite and positive')
    if prep['short_seconds'] > prep['long_seconds']:
        raise ValueError('Short window exceeds long window')
    if prep['resample_hz'] > radio['nominal_rate_hz']:
        raise ValueError('Pilot resampling cannot exceed requested TX rate')
    if isinstance(prep['min_observed_ratio'], bool) or not 0 < prep['min_observed_ratio'] <= 1:
        raise ValueError('Invalid minimum observed ratio')
    integer(prep['causal_median_samples'], 'causal_median_samples', 1, 31)
    return config


def validate_metadata(meta):
    for field in ('recording_id', 'session_id', 'room_id', 'position_id', 'subject_group'):
        value = meta.get(field)
        if not isinstance(value, str) or not value or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in value):
            raise ValueError(f'{field} must be a nonempty safe identifier')
    if meta.get('occupancy') not in ('0', '1', '2', '3+'):
        raise ValueError('Invalid occupancy label')
    if meta.get('motion') not in ('M0', 'M1', 'M2', 'M3'):
        raise ValueError('Invalid motion label')
    if meta['occupancy'] == '0' and meta['motion'] != 'M0':
        raise ValueError('Empty room is only compatible with M0')
    people = meta.get('subject_ids')
    if not isinstance(people, list) or len(set(people)) != len(people):
        raise ValueError('subject_ids must be a unique list of pseudonyms')
    for person in people:
        if not isinstance(person, str) or not person.startswith('p-'):
            raise ValueError('Use pseudonyms such as p-001, not participant names')
    n = len(people)
    if (meta['occupancy'] == '3+' and n < 3) or (meta['occupancy'] != '3+' and n != int(meta['occupancy'])):
        raise ValueError('Participant count does not match occupancy label')
    if meta.get('consent_confirmed') is not True:
        raise ValueError('Participant consent/protocol confirmation is required')
    return meta
