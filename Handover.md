# Handover hardware Wi-Fi CSI

**22 November 2026 · Andi dan Owen**

Repo bersama: [Owen123-lang/esp32-wifi-csi](https://github.com/Owen123-lang/esp32-wifi-csi). Acuan review: [`7b4c884`](https://github.com/Owen123-lang/esp32-wifi-csi/commit/7b4c8841cddf2d7e354fbaed20c9f644b7344d7e). Repo skripsi Andi menyimpan tautannya di `Tools/reference/esp32-wifi-csi` sebagai submodule.

## Yang sudah tersedia

| Area | Owen | Andi |
| --- | --- | --- |
| Topologi dan firmware | Router sebagai sumber paket dan satu ESP32-S3 N16R8 sebagai RX. Pilot memakai ESP-IDF 5.4.2. | Satu ESP32-S3 TX ESP-NOW dan dua RX, dengan ESP-IDF 5.4.3. Profil awal HT20/MCS0, kanal 6, nominal 100 Hz. Source berada di `Tools/firmware` pada repo skripsi. |
| Akuisisi | [Perekam satu port](scripts/rekam_csi.py) membaca `CSI_DATA` dan `DIAM1`. [Firmware diagnostik](firmware/diagnostik-s3/app_main.c) merekam IQ awal, gain, dan hasil konversi dari paket yang sama. | Firmware menyalin CSI ke antrean. Logger mencatat NDJSON dari tiga board. Host mencocokkan timestamp CSI dengan marker pada tiap RX, lalu menggabungkan kedua link menurut identitas paket TX. |
| Bukti | [Pilot 17 November](docs/pilot-2026-11-17/README.md) mencatat 2.385 dari 3.042 sampel sesi diam dengan seluruh komponen CSI nol. [Log 18 November](docs/pilot-2026-11-18/README.md) mencatat pengukuran diagnostik sebelum dan sesudah kompensasi. Lima tes perekam lulus saat review. | Build CI untuk TX, RX-A, dan RX-B tercatat lulus. Sebanyak 17 tes host lulus saat review. Penyelarasan tiga board masih menunggu uji fisik. |

## Untuk Owen

- Konfirmasi apakah router + 1 RX akan dipertahankan untuk eksperimenmu. Sebutkan konfigurasi yang perlu tetap bisa dijalankan ketika profil 1 TX + 2 RX ditambahkan.
- Bagikan referensi build yang benar-benar dipasang pada pilot, termasuk model board, versi ESP-IDF, dan langkah build yang dapat diulang di PC Andi. Script [uji-diam.ps1](scripts/uji-diam.ps1) saat ini merujuk ke salinan proyek dan instalasi IDF lokal. Bagikan konfigurasi yang sudah dibersihkan dari kredensial.
- Jika tersedia, bagikan ringkasan `dipakai`, `nol_sejak_awal`, dan `menjadi_nol` dari sesi `DIAM1`, beserta posisi board dan kondisi pengukuran. Konfirmasi juga format keluaran yang wajib dipertahankan.
- Beri tahu branch, file, atau eksperimen yang sedang kamu kerjakan agar perubahan berikutnya tidak bertabrakan.

## Untuk Andi

- Laporkan perbedaan firmware, versi IDF, format rekaman, dan dukungan topologi sebelum menyesuaikan kode bersama. Sertakan file atau commit dan dampak pada masing-masing eksperimen.
- Bawa inventaris tiga board, jalur serial, profil TX/RX, dan kebutuhan minimum perekam dua link ke diskusi.
- Setelah konfigurasi disepakati, usulkan pilot singkat di ruang kosong. Catat jumlah CSI dan marker per RX, pasangan yang cocok persis, paket TX yang ditemukan pada kedua RX, drop antrean, jeda timestamp, dan proporsi IQ nol. Hasil pilot menentukan langkah penyesuaian berikutnya.

## Keputusan bersama yang masih terbuka

| Keputusan | Yang perlu dicatat |
| --- | --- |
| Konfigurasi yang didukung | Apakah router + 1 RX dan ESP-NOW 1 TX + 2 RX dipertahankan sebagai dua profil. |
| Cara build di kedua PC | Versi ESP-IDF per profil, sumber konfigurasi, dan langkah build tanpa jalur absolut atau kredensial. |
| Format dan diagnostik bersama | Format serial yang tetap kompatibel, cara menyimpan IQ awal dan hasil kompensasi, serta representasi identitas paket TX untuk dua RX. |
| Pembagian kerja | Penanggung jawab firmware, perekam, pilot fisik, dan review PR. |
