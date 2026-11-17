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

## Pilot kamar kosong, diam, dan jalan (tiga rekaman 30 detik)

Letakkan router di meja besar dan ESP32 di meja laptop. Pertahankan posisi perangkat dan posisi pintu selama ketiga rekaman. Tutup monitor serial lain dan aktifkan suara sistem laptop agar tanda selesai terdengar dari luar kamar. Untuk firmware ESP32-S3 yang sudah terpasang, jalankan dari folder repo:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\uji_diam_jalan.py --port COM8
```

Tekan Enter sebelum setiap sesi. Ada waktu 15 detik untuk mengambil posisi (bisa diubah dengan `--siap 25`). Perekam menunggu paket CSI valid, memberi tanda MULAI, lalu merekam selama 30 detik.

1. **Kosong.** Keluar selama waktu persiapan. Pastikan kamar tanpa orang sampai tanda SELESAI, baru masuk kembali.
2. **Diam.** Ambil posisi dekat meja router dan tetap diam sampai tanda SELESAI.
3. **Jalan.** Mulai dari titik yang sama. Saat tanda MULAI, jalan satu kali menuju meja ESP32. Setelah tiba, tetap diam sampai tanda SELESAI. Catat perkiraan detik saat tiba agar bagian berjalan dapat dikenali.

Folder hasil ditampilkan di terminal. Di dalamnya, `kosong/`, `diam/`, dan `jalan/` masing-masing menyimpan `serial.bin` (byte serial selama rekaman), `sampel.jsonl` (CSI dan metadata per paket), `sesi.json` (status dan jumlah baris), serta `catatan.txt` jika diisi. Berkas `perbandingan.png` menampilkan rerata magnitudo pasangan komponen CSI mentah dan RSSI dengan skala yang sama untuk seluruh sesi. Titik mengikuti waktu baca blok serial di laptop. Sampel dengan bagian awal bertanda tidak valid atau komponen tak berpasangan tetap disimpan dan dilewati saat menggambar. Untuk membuat ulang grafik, jalankan skrip dengan `--grafik <folder-hasil>` tanpa membuka port.
