# Pilot ESP-NOW dengan tiga ESP32-S3

Profil ini menambahkan TX, RX-A, dan RX-B untuk skripsi Andi. Untuk firmware, gunakan [petunjuk build dan flash](../firmware/espnow-s3/README.md). Panduan [router dan satu RX](../docs/akuisisi.md) tetap menjadi acuan untuk menjalankan perekam Owen.

## Siapkan perekam

Jalankan dari root repo dengan Python 3.11 atau lebih baru. Gunakan environment terpisah untuk profil ESP-NOW, karena paket yang dipasang mengimpor modul `csi_tools`.

```powershell
py -3 -m venv .venv-espnow
./.venv-espnow/Scripts/python.exe -m pip install "./espnow[serial]"
./.venv-espnow/Scripts/python.exe -m csi_tools ports
```

Salin `espnow/configs/pilot.example.json` dan `espnow/configs/recording.example.json` ke folder lokal `data/espnow/`. Ubah port dan label rekaman sesuai kondisi. Isian contoh memakai ruang kosong, okupansi 0 dan gerakan M0. Isi `consent_confirmed` sesuai konfirmasi prosedur rekaman. Untuk pilot ruang kosong, pastikan memang tanpa partisipan. Catat model board, identitas build yang di-flash, posisi, dan orientasi perangkat. Tutup monitor serial sebelum capture.

```powershell
./.venv-espnow/Scripts/python.exe -m csi_tools capture --config data/espnow/pilot.example.json --metadata data/espnow/recording.example.json --output data/espnow/empty-001 --seconds 15
./.venv-espnow/Scripts/python.exe -m csi_tools qc data/espnow/empty-001
```

Output mencakup serial asli per board, `raw.ndjson`, metadata, ringkasan capture, dan checksum. Gunakan direktori output baru setiap kali. Jika capture gagal, periksa `capture_summary.json` untuk menemukan perangkat yang tidak mengirim data atau kondisi port yang bermasalah.

## Periksa hasil pilot

1. Verifikasi log TX, CSI, dan marker. Bandingkan jumlah CSI dan marker dengan jumlah timestamp yang cocok tepat pada masing-masing RX.
2. Periksa `shared_packets`, yaitu paket TX yang memiliki pasangan valid di kedua RX. Jika nol, QC tetap mencetak statistik per RX dan keluar dengan status gagal. Periksa radio dan timestamp callback menggunakan data mentah sebelum memperbaiki penyelarasan.
3. Catat gap timestamp TX bersama, drop antrean, jumlah paket IQ nol, dan jumlah pasangan yang diterima. Penanda CSI awal yang tidak valid dikeluarkan dari hitungan IQ nol. Denominator pengiriman berasal dari log TX untuk panggilan API yang diterima, sehingga tidak mengukur langsung semua paket di udara.

Angka nominal 100 Hz dan konfigurasi radio adalah titik awal pilot. Uji fisik masih perlu memastikan kecocokan timestamp dan kelayakan perekaman sebelum data utama diambil.

## Verifikasi tanpa perangkat

```powershell
./.venv-espnow/Scripts/python.exe -m csi_tools simulate --config espnow/configs/pilot.example.json --metadata espnow/configs/recording.example.json --output data/espnow/synthetic-001
./.venv-espnow/Scripts/python.exe -m csi_tools qc data/espnow/synthetic-001
./.venv-espnow/Scripts/python.exe -m unittest discover -s espnow/tests -v
```

Hasil simulator ditandai `synthetic` di metadata dan laporan QC.
