import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import numpy as np
from csi_tools.protocol import parse_line, validate_config, validate_metadata
from csi_tools.recording import finalize, capture
from csi_tools.simulate import simulate
from csi_tools.processing import iq_amplitude, align_recording

ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.config = json.loads((ROOT/'configs/pilot.example.json').read_text())
        self.config['radio']['nominal_rate_hz'] = 20
        self.config['preprocessing'].update(resample_hz=20, short_seconds=0.2,
             long_seconds=0.8, stride_seconds=0.2, max_gap_seconds=0.11)
        self.meta = json.loads((ROOT/'configs/recording.example.json').read_text())

    def recording(self):
        return simulate(self.path/'raw', self.config, self.meta, seconds=3)

    def test_imaginary_first_and_invalid_prefix_keeps_original_indices(self):
        row = {'iq': [4,3,12,5,8,15], 'first_word_invalid': True}
        a = iq_amplitude(row)
        self.assertTrue(np.isnan(a[:2]).all())
        self.assertEqual(a[2], 17)

    def test_protocol_rejects_truncated_json_and_odd_iq(self):
        self.assertIsNone(parse_line('I (123) boot log'))
        with self.assertRaises(ValueError): parse_line('{"v":')
        with self.assertRaises(ValueError):
            parse_line(json.dumps({'v':1,'kind':'CSI','device_id':'rx-a',
                                  'boot_id':1,'device_us':1,'iq':[1],'len':1}))

    def test_invalid_empty_room_motion_and_participant_labels(self):
        self.meta.update(consent_confirmed=True, motion='M2')
        with self.assertRaises(ValueError): validate_metadata(self.meta)
        self.meta.update(motion='M0', occupancy='2', subject_ids=['p-001'])
        with self.assertRaises(ValueError): validate_metadata(self.meta)

    def test_configuration_rejects_same_serial_port_and_invalid_bins(self):
        self.config['devices'][1]['port'] = self.config['devices'][0]['port']
        with self.assertRaises(ValueError): validate_config(self.config)
        self.config['devices'][1]['port'] = 'NEW'
        self.config['preprocessing']['raw_pair_indices'] = [0,2]
        with self.assertRaises(ValueError): validate_config(self.config)

    def test_dual_link_alignment_uses_tx_time_not_host_or_receiver_clock(self):
        times, data, _, _, report = align_recording(self.recording())
        self.assertEqual(len(times), 60)
        self.assertEqual(data.shape, (60,2,47))
        self.assertEqual(times[0], 1.0)
        self.assertEqual(report['delivery_against_accepted_sends']['rx-a'], 1)

    def test_corrupted_recording_fails_checksum_validation(self):
        folder = self.recording()
        with (folder/'raw.ndjson').open('a') as f: f.write('\n')
        with self.assertRaisesRegex(ValueError, 'checksum'): align_recording(folder)

    def test_callback_reordering_does_not_change_alignment(self):
        folder = self.recording()
        before = align_recording(folder)[1]
        p = folder/'raw.ndjson'; lines = p.read_text().splitlines()
        p.write_text('\n'.join(reversed(lines))+'\n')
        finalize(folder, 'complete', {'synthetic':True})
        np.testing.assert_array_equal(before, align_recording(folder)[1])

    def test_ambiguous_csi_marker_matching_does_not_invent_pairs(self):
        folder = self.recording();p = folder/'raw.ndjson'
        lines = p.read_text().splitlines(); marker = next(x for x in lines if '"MARKER"' in x)
        p.write_text('\n'.join(lines+[marker])+'\n');finalize(folder,'complete',{})
        report = align_recording(folder)[-1]
        self.assertEqual(report['shared_packets'],59)
        self.assertEqual(report['rejected']['missing_or_ambiguous_marker'],1)

    def test_empty_alignment_reports_diagnostics_for_each_receiver(self):
        folder = self.recording()
        raw = folder / 'raw.ndjson'
        rows = [json.loads(line) for line in raw.read_text().splitlines()]
        for row in rows:
            if row['kind'] == 'MARKER' and row['device_id'] == 'rx-b':
                row['device_us'] += 1
            if row['kind'] == 'CSI' and row['device_id'] == 'rx-b':
                row['iq'] = [0] * row['len']
        raw.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
        finalize(folder, 'complete', {'synthetic': True})

        with self.assertRaisesRegex(ValueError, 'No unambiguous shared TX packets'):
            align_recording(folder)
        _, values, _, _, report = align_recording(folder, allow_empty=True)
        self.assertEqual(values.shape, (0, 2, 47))
        self.assertEqual(report['links']['rx-a']['accepted_pairs'], 60)
        self.assertEqual(report['links']['rx-b']['markers'], 60)
        self.assertEqual(report['links']['rx-b']['timestamp_pairs'], 0)
        self.assertEqual(report['links']['rx-b']['all_zero_iq'], 60)
        self.assertIsNone(report['largest_shared_tx_gap_ms'])

    def test_live_serial_open_failure_marks_recording_failed_and_closes_port(self):
        ports=[]
        class BrokenPort:
            def __init__(self, **kwargs):self.closed=False;ports.append(self)
            def open(self):raise OSError('serial unavailable')
            def close(self):self.closed=True
        self.meta['consent_confirmed']=True
        with patch.dict('sys.modules', {'serial':SimpleNamespace(Serial=BrokenPort)}):
            with self.assertRaises(OSError):
                capture(self.path/'capture',self.config,self.meta,0.1)
        self.assertTrue(all(port.closed for port in ports))
        self.assertEqual(json.loads((self.path/'capture/metadata.json').read_text())['state'],'failed')

    def test_live_wrong_board_identity_aborts_instead_of_mislabeling_link(self):
        class WrongBoard:
            def __init__(self, **kwargs):pass
            def open(self):pass
            def close(self):pass
            def readline(self, size):
                return b'{"v":1,"kind":"BOOT","device_id":"rx-b","boot_id":1}\n'
        self.meta['consent_confirmed']=True
        with patch.dict('sys.modules', {'serial':SimpleNamespace(Serial=WrongBoard)}):
            with self.assertRaises(RuntimeError):
                capture(self.path/'capture',self.config,self.meta,0.1)
        self.assertEqual(json.loads((self.path/'capture/metadata.json').read_text())['state'],'failed')

    def test_live_silent_ports_do_not_create_a_successful_empty_recording(self):
        class SilentPort:
            def __init__(self, **kwargs):pass
            def open(self):pass
            def close(self):pass
            def readline(self, size):time.sleep(0.01);return b''
        self.meta['consent_confirmed']=True
        with patch.dict('sys.modules', {'serial':SimpleNamespace(Serial=SilentPort)}):
            with self.assertRaises(RuntimeError):
                capture(self.path/'capture',self.config,self.meta,0.05)
        summary=json.loads((self.path/'capture/capture_summary.json').read_text())
        self.assertTrue(any('no CSI' in error for error in summary['errors']))


if __name__ == '__main__':
    unittest.main()
