# Build dan simulasi ESP-NOW dengan Docker

Gunakan Docker Desktop dengan Linux containers, atau Docker Engine dengan plugin Docker Compose. Jalankan perintah dari root repo. Jika belum memiliki checkout branch pilot, ambil dengan perintah ini.

```sh
git clone --branch codex/andi-espnow-three-board-pilot https://github.com/Owen123-lang/esp32-wifi-csi.git
cd esp32-wifi-csi
```

## Build TX, RX-A, dan RX-B

```sh
docker compose build firmware
docker compose run --rm firmware
```

Image memakai ESP-IDF **v5.4.3**. Untuk build satu peran, tambahkan `tx`, `rx-a`, atau `rx-b` di akhir perintah, misalnya `docker compose run --rm firmware rx-a`.

Hasil disimpan di `runs/docker/firmware/<peran>/`. Setiap direktori berisi binari aplikasi, ELF, bootloader, tabel partisi, konfigurasi SDK, log build, checksum, dan `qemu-flash.bin`. Image flash gabungan berukuran 4 MB dan dipakai untuk uji QEMU. Untuk uji board fisik, ikuti [panduan firmware](../firmware/espnow-s3/README.md) dan cocokkan peran dengan board serta port serialnya.

## Simulasi dan pengujian host

```sh
docker compose build simulator
docker compose run --rm simulator
docker compose run --rm simulator python -m unittest discover -s tests -v
```

Perintah simulasi membuat rekaman sintetis 12 detik di direktori baru `runs/docker/synthetic-*/recording/` dan mencetak laporan `qc.json`. Pada konfigurasi contoh, hasil yang diharapkan adalah `synthetic: true` dan `shared_packets: 1200`. Ini menguji pemrosesan log TX dan kedua RX di host. Perintah dan data yang digunakan sama dengan [simulasi Python lokal](../espnow/README.md).

## Uji boot firmware di QEMU

Build peran yang ingin diuji terlebih dahulu.

```sh
docker compose build qemu
docker compose run --rm qemu tx
docker compose run --rm qemu rx-a
docker compose run --rm qemu rx-b
```

Setiap perintah menjalankan satu ESP32-S3 virtual selama maksimal 25 detik dan menyimpan `uart.log`, `qemu.log`, serta status proses di `runs/docker/qemu-<peran>-*/`. Pemeriksaan uji boot mencari keluaran ROM ESP32-S3. Lihat log untuk mengetahui apakah bootloader berhasil memuat aplikasi. Pada QEMU Espressif, Wi-Fi belum diemulasikan, sehingga verifikasi ESP-NOW, CSI, dan kecocokan timestamp kedua RX memerlukan tiga board fisik. [Dokumentasi dukungan periferal](https://github.com/espressif/esp-toolchain-docs/blob/main/qemu/README.md)

Pada uji Docker ARM64 tanggal 22 November 2026, ketiga profil berhasil mencapai `app_main`. Semuanya kemudian reboot setelah `ESP_ERR_INVALID_ARG` pada tahap konfigurasi Wi-Fi. Status sukses dari perintah QEMU berarti keluaran ROM ditemukan.

Compose menggunakan container sekali jalan. Opsi `--rm` menghapus container setelah eksekusi, sementara hasil tetap tersimpan di `runs/docker/`. Unduhan pertama memerlukan internet. Setelah image tersedia, layanan simulasi dan QEMU berjalan dengan jaringan container dinonaktifkan.
