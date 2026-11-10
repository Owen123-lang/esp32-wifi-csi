"""Rekam keluaran serial csi_recv_router atau baca ulang berkas uji (Python 3.10+)."""

import argparse
import csv
import json
import math
import sys
import time
from collections import Counter
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


# Nama dan urutan kolom pada dua cabang printf firmware yang disertakan.
SCHEMAS = (
    "type seq mac rssi rate noise_floor fft_gain agc_gain channel local_timestamp sig_len rx_format len first_word data".split(),
    "type id mac rssi rate sig_mode mcs bandwidth smoothing not_sounding aggregation stbc fec_coding sgi noise_floor ampdu_cnt channel secondary_channel local_timestamp ant sig_len rx_format len first_word data".split(),
)


def utc():
    return datetime.now(timezone.utc).isoformat()


class Decoder:
    def __init__(self):
        self.header = None
        self.previous = None

    def parse(self, line):
        if line.startswith(b"type,"):
            self.previous = None
            self.header = []  # Header rusak tidak boleh memakai skema sesi sebelumnya.
            self.header = line.decode("ascii").strip().split(",")
            return None
        if not line.startswith(b"CSI_DATA,"):
            return None

        cells = next(csv.reader([line.decode("ascii")], strict=True))
        fields = self.header
        if fields is None:  # Firmware sudah berjalan saat port dibuka.
            fields = next((s for s in SCHEMAS if len(s) == len(cells)), [])
        if fields not in SCHEMAS or len(cells) != len(fields):
            raise ValueError("format_kolom")
        sample = dict(zip(fields, cells))
        for key in fields:
            if key not in ("type", "mac", "data"):
                sample[key] = int(sample[key])
        payload = json.loads(sample["data"])
        if not isinstance(payload, list) or not payload or len(payload) != sample["len"]:
            raise ValueError("panjang_payload")
        if not all(type(v) is int for v in payload) or sample["first_word"] not in (0, 1):
            raise ValueError("isi_payload")
        sample["data"] = payload
        seq = sample.get("seq", sample.get("id"))
        timestamp = sample["local_timestamp"] & 0xFFFFFFFF
        sample["selang_timestamp_us"] = None
        if self.previous is not None:
            prev_seq, prev_time, prev_mac = self.previous
            if seq == prev_seq + 1 and sample["mac"] == prev_mac:
                sample["selang_timestamp_us"] = (timestamp - prev_time) & 0xFFFFFFFF
        self.previous = (seq, timestamp, sample["mac"])
        return sample


def record(stream, destination, meta, *, live, seconds):
    """Simpan setiap blok mentah sebelum pemisahan baris dan validasi CSV."""
    destination.mkdir(parents=True, exist_ok=False)
    manifest = destination / "sesi.json"
    meta.update(status="berjalan", mulai_utc=utc())
    manifest.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    counts = Counter(baris_csi=0, diterima_parser=0, ditolak_parser=0,
                     first_word_invalid=0, baris_lain=0, byte_tanpa_akhir_baris=0)
    decoder = Decoder()
    pending = bytearray()
    # Salah baud dapat menghasilkan byte tanpa newline untuk waktu yang lama.
    # Byte tetap ditulis ke serial.bin. Batasi RAM untuk satu baris parser.
    max_line = 65536
    skipped_bytes = 0
    start = time.monotonic()
    status = "selesai"
    try:
        with (destination / "serial.bin").open("xb") as raw, (
            destination / "sampel.jsonl"
        ).open("x", encoding="utf-8", newline="\n") as out:
            while seconds is None or time.monotonic() - start < seconds:
                size = min(max(stream.in_waiting, 1), 65536) if live else 65536
                chunk = stream.read(size)
                if not chunk:
                    if live:  # Timeout serial tetap memberi kesempatan memeriksa durasi.
                        continue
                    break
                raw.write(chunk)
                raw.flush()
                if skipped_bytes:
                    end = chunk.find(b"\n")
                    if end < 0:
                        skipped_bytes += len(chunk)
                        continue
                    skipped_bytes = 0
                    chunk = chunk[end + 1:]
                pending.extend(chunk)
                lines = pending.split(b"\n")
                pending = lines.pop()
                if len(pending) > max_line:
                    skipped_bytes = len(pending)
                    counts["baris_terlalu_panjang"] += 1
                    pending.clear()
                for line in lines:
                    if len(line) > max_line:
                        counts["baris_terlalu_panjang"] += 1
                        continue
                    is_sample = line.startswith(b"CSI_DATA,")
                    counts["baris_csi" if is_sample else "baris_lain"] += 1
                    try:
                        sample = decoder.parse(line.rstrip(b"\r"))
                    except (ValueError, csv.Error, RecursionError):
                        if is_sample:
                            counts["ditolak_parser"] += 1
                        continue
                    if sample is not None:
                        counts["diterima_parser"] += 1
                        counts["first_word_invalid"] += sample["first_word"]
                        out.write(json.dumps(sample, separators=(",", ":")) + "\n")
                out.flush()
    except KeyboardInterrupt:
        status = "dihentikan_pengguna"
    except Exception as exc:
        status = "gagal"
        meta["kesalahan"] = str(exc)
        raise
    finally:
        counts["byte_tanpa_akhir_baris"] = len(pending) + skipped_bytes
        meta.update(status=status, akhir_utc=utc(), ringkasan=dict(counts))
        temp = manifest.with_suffix(".tmp")
        temp.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        temp.replace(manifest)
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--port", help="Port serial board, misalnya COM5")
    mode.add_argument("--file", type=Path, help="Uji pembacaan berkas serial secara offline")
    parser.add_argument("--baud", type=int, default=921600)
    parser.add_argument("--detik", type=float, help="Durasi pembacaan serial, atau Ctrl+C untuk berhenti")
    parser.add_argument("--sesi", required=True, help="Kode sesi pengambilan data atau uji")
    parser.add_argument("--lingkungan", required=True, help="Kode tata letak atau uji-format")
    parser.add_argument("--board", help="Model board yang digunakan")
    parser.add_argument("--firmware", help="Revisi firmware yang benar-benar dipasang")
    parser.add_argument("--catatan", default="", help="Konfigurasi Wi-Fi, posisi Tx/Rx, atau catatan sesi")
    parser.add_argument("--output", type=Path, default=Path("data"))
    args = parser.parse_args()
    if args.port and not (args.board and args.firmware):
        parser.error("Untuk rekaman serial, sertakan --board dan --firmware.")
    if args.baud <= 0 or (args.detik is not None and
            (not args.port or not math.isfinite(args.detik) or args.detik <= 0)):
        parser.error("Baud harus positif. --detik hanya untuk port serial dan harus positif.")
    recording_id = uuid4().hex
    dest = args.output / ("serial" if args.port else "offline") / recording_id
    meta = dict(id_rekaman=recording_id, sesi=args.sesi, lingkungan=args.lingkungan,
                sumber="serial" if args.port else "berkas_offline", port=args.port,
                berkas=str(args.file) if args.file else None, baud=args.baud if args.port else None,
                board=args.board, firmware=args.firmware, catatan=args.catatan)
    try:
        with ExitStack() as stack:
            if args.port:
                try:
                    import serial
                except ImportError:
                    parser.exit(2, "Pasang pyserial dengan python -m pip install -r requirements.txt\n")
                stream = stack.enter_context(serial.Serial(args.port, args.baud, timeout=0.2))
            else:
                stream = stack.enter_context(args.file.open("rb"))
            print(f"Folder rekaman: {dest}", flush=True)
            counts = record(stream, dest, meta, live=bool(args.port), seconds=args.detik)
    except OSError as exc:
        print(f"Gagal merekam: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(dict(counts), indent=2))
    if not counts["diterima_parser"]:
        print("Belum ada baris CSI lengkap yang lolos pemeriksaan.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
