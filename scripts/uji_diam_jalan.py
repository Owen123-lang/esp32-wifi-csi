"""Rekam CSI saat kamar kosong, saat seseorang diam, lalu saat berjalan."""

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path
from uuid import uuid4

import matplotlib
import serial

from rekam_csi import Decoder, record

matplotlib.use("Agg")
from matplotlib import pyplot as plt


DURASI = 30
KONDISI = {
    "kosong": "Semua orang keluar dari kamar selama waktu bersiap. Masuk kembali setelah tanda selesai.",
    "diam": "Ambil posisi awal dekat meja router dan tetap diam sampai tanda selesai.",
    "jalan": "Mulai dekat meja router. Saat tanda mulai, jalan ke meja ESP32. "
             "Setelah sampai, tetap diam sampai tanda selesai.",
}


def tunggu_csi(port):
    port.reset_input_buffer()
    decoder = Decoder()
    batas = time.monotonic() + 25
    while time.monotonic() < batas:
        line = port.read_until(b"\n", 8192)
        try:
            if line.endswith(b"\n") and decoder.parse(line.rstrip()) is not None:
                return
        except (ValueError, csv.Error, RecursionError):
            continue
    raise RuntimeError("CSI belum terbaca. Periksa koneksi router, port, dan baud.")


def tanda(teks):
    print(teks, flush=True)
    if sys.platform == "win32":
        import winsound
        winsound.MessageBeep()
    else:
        print("\a", end="", flush=True)


def buat_grafik(folder):
    # Rekaman dari versi awal hanya memiliki sesi diam dan jalan.
    kondisi_rekaman = list(KONDISI) if (folder / "kosong").exists() else ["diam", "jalan"]
    kolom_total = len(kondisi_rekaman)
    fig, axes = plt.subplots(2, kolom_total, sharex=True, sharey="row", figsize=(5 * kolom_total, 6),
                             constrained_layout=True)
    try:
        for kolom, kondisi in enumerate(kondisi_rekaman):
            sesi = folder / kondisi
            meta = json.loads((sesi / "sesi.json").read_text(encoding="utf-8"))
            if meta["status"] != "selesai":
                raise ValueError(f"Sesi {kondisi} belum selesai.")
            waktu, amplitudo, rssi = [], [], []
            with (sesi / "sampel.jsonl").open(encoding="utf-8") as sumber:
                for baris in sumber:
                    sampel = json.loads(baris)
                    data = sampel["data"]
                    if sampel["first_word"] or len(data) % 2:
                        continue
                    magnitudo = [math.hypot(i, q) for i, q in zip(data[::2], data[1::2])]
                    amplitudo.append(sum(magnitudo) / len(magnitudo))
                    waktu.append(sampel["waktu_baca_s"])
                    rssi.append(sampel["rssi"])
            if not waktu:
                raise ValueError(f"Tidak ada sampel yang dapat diplot untuk sesi {kondisi}.")
            for ax, nilai in zip(axes[:, kolom], (amplitudo, rssi)):
                ax.scatter(waktu, nilai, s=2, alpha=0.55)
                ax.set_xlim(0, DURASI)
                ax.grid(alpha=0.2)
            axes[0, kolom].set_title(f"Sesi {kondisi} ({len(waktu)} sampel diplot)")
            axes[1, kolom].set_xlabel("Waktu baca di laptop (detik)")
            print(f"{kondisi}: sampel pada grafik dari {waktu[0]:.2f} s hingga {waktu[-1]:.2f} s.")
        axes[0, 0].set_ylabel("Rerata magnitudo CSI\n(satuan mentah)")
        axes[1, 0].set_ylabel("RSSI (dBm)")
        fig.savefig(folder / "perbandingan.png", dpi=160)
    finally:
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="COM8")
    parser.add_argument("--siap", type=int, default=15, help="Waktu untuk mengambil posisi (detik)")
    parser.add_argument("--grafik", type=Path, help="Buat ulang grafik dari folder rangkaian rekaman")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "pilot")
    args = parser.parse_args()
    if args.grafik:
        buat_grafik(args.grafik)
        return
    if args.siap < 0:
        parser.error("--siap minimal 0 detik.")
    folder = args.output / uuid4().hex
    print(f"Folder rangkaian rekaman: {folder}")
    with serial.Serial(args.port, 921600, timeout=0.2) as port:
        for kondisi, instruksi in KONDISI.items():
            print(f"\nSesi {kondisi}, {DURASI} detik. {instruksi}")
            input("Tekan Enter saat siap mengambil posisi. ")
            print(f"Waktu bersiap {args.siap} detik. Tunggu tanda MULAI.", flush=True)
            time.sleep(args.siap)
            tunggu_csi(port)
            meta = dict(id_rangkaian=folder.name, sesi=kondisi, sumber="serial",
                        port=args.port, baud=921600, durasi_target_s=DURASI,
                        posisi_router="meja besar", posisi_esp32="meja laptop",
                        instruksi=instruksi)
            port.reset_input_buffer()
            tanda(f"MULAI {kondisi.upper()}")
            counts = record(port, folder / kondisi, meta, live=True, seconds=DURASI, sample_clock=True)
            tanda(f"SELESAI {kondisi.upper()}")
            if meta["status"] != "selesai" or not counts["diterima_parser"]:
                raise RuntimeError(f"Sesi {kondisi} terhenti atau kosong. Periksa {folder / kondisi}.")
            print(f"{counts['diterima_parser']} sampel tersimpan.")
            catatan = input("Catatan aktual (misalnya waktu tiba atau gangguan; Enter untuk lewati): ")
            if catatan.strip():
                (folder / kondisi / "catatan.txt").write_text(catatan.strip() + "\n", encoding="utf-8")
    buat_grafik(folder)
    print(f"Grafik: {folder / 'perbandingan.png'}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, EOFError) as exc:
        sys.exit(f"Uji belum selesai: {exc}")
