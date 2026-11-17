"""Uji diam 30 detik untuk memeriksa nilai CSI pada kedua sisi kompensasi gain."""

import argparse
import json
import math
import sys
import time
from pathlib import Path
from uuid import uuid4

import serial

from rekam_csi import Decoder, record
from uji_diam_jalan import DURASI, plt, tanda


def tunggu_diagnostik(port):
    port.reset_input_buffer()
    decoder = Decoder()
    pending = b""
    batas = time.monotonic() + 35
    while time.monotonic() < batas:
        pending += port.read(min(max(port.in_waiting, 1), 16384))
        *lines, pending = pending.split(b"\n")
        if len(pending) > 8192:
            pending = b""
        for line in lines:
            if not line.startswith(b"CSI_DATA,"):
                continue
            if not line.startswith(b"CSI_DATA,DIAM1,"):
                raise RuntimeError("Board masih mengirim format biasa. Jalankan PowerShell dengan -Flash.")
            try:
                sample = decoder.parse(line.rstrip())
            except ValueError:
                continue
            if sample["seq"] > 100:
                return
    raise RuntimeError("Paket DIAM1 belum terbaca. Periksa port, firmware, dan koneksi router.")


def rangkum(folder):
    waktu, sebelum, sesudah = [], [], []
    hitung = dict(dipakai=0, dilewati=0, nol_sejak_awal=0, menjadi_nol=0, nol_sesudah=0)
    with (folder / "sampel.jsonl").open(encoding="utf-8") as src:
        for line in src:
            s = json.loads(line)
            if (s["type"] != "DIAM1" or s["first_word"] or s["gain_status"] != 0
                    or s["seq"] <= 100 or s["len"] % 2):
                hitung["dilewati"] += 1
                continue
            awal, akhir = s["data_awal"], s["data"]
            nol_awal, nol_akhir = not any(awal), not any(akhir)
            hitung["dipakai"] += 1
            hitung["nol_sejak_awal"] += nol_awal
            hitung["menjadi_nol"] += not nol_awal and nol_akhir
            hitung["nol_sesudah"] += nol_akhir
            waktu.append(s["waktu_baca_s"])
            for nilai, seri in ((awal, sebelum), (akhir, sesudah)):
                seri.append(2 * sum(math.hypot(i, q) for i, q in zip(nilai[::2], nilai[1::2])) / len(nilai))
    (folder / "ringkasan.json").write_text(json.dumps(hitung, indent=2), encoding="utf-8")
    if not waktu:
        raise ValueError("Data mentah tersimpan, tetapi tidak ada pasangan CSI yang layak dibandingkan.")
    fig, axes = plt.subplots(2, 1, sharex=True, figsize=(9, 5), constrained_layout=True)
    for ax, seri, judul in zip(axes, [sebelum, sesudah], ["Sebelum kompensasi", "Setelah kompensasi dan konversi integer"]):
        ax.scatter(waktu, seri, s=3, alpha=.55)
        ax.set_title(judul)
        ax.set_ylabel("Rerata magnitudo")
        ax.grid(alpha=.2)
    axes[-1].set_xlabel("Waktu baca di laptop (detik)")
    fig.savefig(folder / "perbandingan_gain.png", dpi=150)
    plt.close(fig)
    print(f"Paket yang sudah nol sejak awal: {hitung['nol_sejak_awal']} dari {hitung['dipakai']}.")
    print(f"Paket yang baru menjadi nol setelah konversi: {hitung['menjadi_nol']} dari {hitung['dipakai']}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="COM8")
    args = parser.parse_args()
    folder = Path(__file__).resolve().parents[1] / "data" / "diam_gain" / uuid4().hex
    with serial.Serial(args.port, 921600, timeout=.15) as port:
        print("Menunggu firmware diagnostik dan paket CSI ...", flush=True)
        tunggu_diagnostik(port)
        input("Tekan Enter saat siap pindah ke posisi diam dekat router. ")
        print("Ambil posisi. Perekaman dimulai dalam 15 detik.", flush=True)
        time.sleep(15)
        port.reset_input_buffer()
        meta = dict(sesi="diam dekat router", format="DIAM1", board="ESP32-S3",
                    sumber="serial", port=args.port, baud=921600, durasi_target_s=DURASI)
        print(f"Folder hasil: {folder}", flush=True)
        tanda("MULAI DIAM")
        record(port, folder, meta, live=True, seconds=DURASI, sample_clock=True)
        tanda("SELESAI DIAM")
    if meta["status"] != "selesai":
        raise RuntimeError("Rekaman terhenti. Bagian yang sempat dibaca tersimpan di folder hasil.")
    rangkum(folder)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, EOFError) as exc:
        sys.exit(f"Uji belum selesai: {exc}")
