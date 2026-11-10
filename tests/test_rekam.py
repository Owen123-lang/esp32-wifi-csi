import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import serial
from scripts.rekam_csi import Decoder, record


FIXTURE = Path(__file__).parent / "fixtures/uji-format.txt"
LONG_ROW = b'CSI_DATA,0,02:00:00:00:00:01,-44,1,0,0,0,0,0,0,0,0,0,-90,0,1,0,42,0,20,0,4,0,"[1,-2,3,-4]"'


class PerekamTest(unittest.TestCase):
    def test_stream_loopback(self):
        payload = FIXTURE.read_bytes()
        with tempfile.TemporaryDirectory() as tmp, serial.serial_for_url("loop://", timeout=0.02) as port:
            folder = Path(tmp) / "sesi"
            port.write(payload)
            counts = record(port, folder, {}, live=True, seconds=0.15)
            self.assertEqual((folder / "serial.bin").read_bytes(), payload)
            self.assertEqual((counts["baris_csi"], counts["diterima_parser"], counts["ditolak_parser"]), (3, 2, 1))
            samples = [json.loads(line) for line in (folder / "sampel.jsonl").read_text().splitlines()]
            self.assertEqual(samples[1]["selang_timestamp_us"], 1000)
            self.assertEqual(samples[1]["first_word"], 1)

    def test_connect_after_header_and_reset(self):
        decoder = Decoder()
        self.assertEqual(decoder.parse(LONG_ROW)["data"], [1, -2, 3, -4])
        decoder.parse(b"type,unknown")
        with self.assertRaises(ValueError):
            decoder.parse(LONG_ROW)

    def test_partial_record_on_disconnect(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "sesi"
            stream = Mock(in_waiting=32)
            stream.read.side_effect = [LONG_ROW[:20], OSError("port disconnected")]
            with self.assertRaises(OSError):
                record(stream, folder, {}, live=True, seconds=None)
            self.assertEqual((folder / "serial.bin").read_bytes(), LONG_ROW[:20])
            manifest = json.loads((folder / "sesi.json").read_text())
            self.assertEqual(manifest["status"], "gagal")
            self.assertEqual(manifest["ringkasan"]["byte_tanpa_akhir_baris"], 20)

    def test_wrong_baud_stream_then_complete_record(self):
        payload = b"x" * 200000 + b"\n" + LONG_ROW + b"\n"
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "sesi"
            counts = record(io.BytesIO(payload), folder, {}, live=False, seconds=None)
            self.assertEqual(counts["baris_terlalu_panjang"], 1)
            self.assertEqual(counts["diterima_parser"], 1)
            self.assertEqual((folder / "serial.bin").read_bytes(), payload)
