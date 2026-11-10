# Akuisisi CSI

## Uji di laptop tanpa ESP32

Dari folder utama repo, siapkan Python 3.10 atau lebih baru. Pada Windows dengan Python Launcher, jalankan perintah berikut sekali. Jika Python dipasang tanpa launcher, ganti `py -3` dengan `python`.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Jalankan perekam dengan berkas uji format.

```powershell
.\.venv\Scripts\python.exe scripts\rekam_csi.py --file tests\fixtures\uji-format.txt --sesi cek-parser --lingkungan uji-format
```

Pada berkas contoh, dua baris CSI dapat dibaca dan satu ditolak karena panjang payload berbeda dari nilai `len`. Angka di berkas ini dibuat khusus untuk menguji parser. Hasil pemutaran berkas disimpan di `data/offline/`, terpisah dari rekaman port fisik di `data/serial/`. Untuk mengulangi pengujian port virtual, pembacaan tanpa header, dan sambungan yang terputus, jalankan:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Firmware untuk uji pertama

Sebagai titik awal, digunakan contoh resmi [csi_recv_router dari Espressif](https://github.com/espressif/esp-csi/tree/8633d67152db2808f141cc1595970aa9cf406045/examples/get-started/csi_recv_router). ESP32 terhubung ke access point, mengirim ping ke gateway, dan mencetak CSI dari paket yang diterima dari AP. Revisi sumber dikunci melalui Git submodule. Varian board, laju paket pengujian utama, dan konfigurasi final tetap ditentukan dari perangkat serta uji pendahuluan.

1. Dari folder utama jalankan `git submodule update --init --depth 1 firmware/esp-csi`. Sumber firmware berada di `firmware/esp-csi/examples/get-started/csi_recv_router`.
2. Setelah chip diketahui, gunakan [lingkungan ESP-IDF untuk Windows](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/get-started/windows-setup.html) yang mendukung target tersebut. Di terminal ESP-IDF, buka folder contoh, jalankan `idf.py set-target <chip>`, lalu `idf.py menuconfig`. Ganti `<chip>` dengan target board yang sebenarnya. Atur koneksi Wi-Fi ke router pengujian pada pengaturan contoh. Simpan SSID dan kata sandi hanya pada konfigurasi lokal.
3. Jalankan `idf.py build`. Setelah board terpasang dan port diketahui, jalankan `idf.py -p COM5 flash` dengan port yang sesuai. Jika monitor serial digunakan untuk memeriksa log, tutup monitor sebelum membuka perekam. Simpan versi ESP-IDF, revisi firmware, perubahan konfigurasi, dan baud konsol yang dipakai pada catatan sesi.
4. Kembali ke folder utama repo. Contoh berikut memakai COM5, 921600 baud (nilai contoh firmware), dan durasi 15 detik untuk pemeriksaan awal. Ganti argumen sesuai perangkat sebelum menjalankannya. Durasi ini hanya untuk mengecek koneksi.

```powershell
$board = Read-Host "Model board yang terpasang"
$firmware = git -C firmware/esp-csi rev-parse HEAD
.\.venv\Scripts\python.exe scripts\rekam_csi.py --port COM5 --baud 921600 --detik 15 --sesi pilot-01 --lingkungan ruang-kosong --board "$board" --firmware "$firmware" --catatan "ESP32 menerima paket dari AP"
```

Jika firmware diubah, sertakan identitas build yang benar-benar dipasang. Tanpa `--detik`, perekaman berlangsung sampai Ctrl+C. Jika belum ada baris CSI lengkap, periksa port, baud konsol, koneksi Wi-Fi, dan isi log serial. Catat model router, kanal Wi-Fi, serta posisi Tx/Rx untuk sesi sungguhan. Pemeriksaan pertama dilakukan di ruangan kosong.

## Berkas per rekaman

Setiap pemanggilan membuat folder baru dengan ID unik. Lokasinya ditampilkan saat perekam dibuka.

| Berkas | Isi |
| --- | --- |
| `serial.bin` | Byte asli yang diterima, termasuk log awal, baris rusak, dan bagian akhir yang terpotong. Berkas ini dapat diperiksa kembali dengan `--file`. |
| `sampel.jsonl` | Satu baris JSON per baris CSI lengkap yang lolos pemeriksaan struktur. Kolom firmware seperti nomor urut, kanal, RSSI, timestamp perangkat, panjang payload, `first_word`, dan larik `data` dipertahankan. |
| `sesi.json` | ID sesi dan rekaman, lingkungan, sumber serial/offline, versi firmware yang dimasukkan, waktu mulai dan akhir dalam UTC, status akhir, serta jumlah baris diterima dan ditolak. |

`selang_timestamp_us` dihitung dari waktu penerimaan di perangkat untuk dua sampel dengan nomor urut bersebelahan dari MAC yang sama. Nilainya kosong pada awal aliran, sesudah header, atau saat urutan terputus. Simpan nilai mentah dan periksa selangnya sebelum menghitung laju efektif. Hitungan pada ringkasan merujuk ke baris CSI yang sampai di laptop. Jumlah seluruh paket radio tidak diketahui dari log serial ini.

Penanda `first_word=1` disimpan karena bagian awal buffer ditandai tidak valid oleh perangkat. Lolos pemeriksaan format belum memastikan kualitas sinyal. Pemetaan komponen CSI, pemilihan subcarrier, dan penanganan bagian yang tidak valid perlu disesuaikan dengan target sebelum prapemrosesan. Folder rekaman dikecualikan dari Git karena dapat memuat MAC, informasi jaringan, dan metadata sesi.
