# Eksperimen deteksi jatuh dengan Wi-Fi CSI dan ESP32

Panduan [pilot ESP-NOW tiga board](espnow/README.md) tersedia untuk rancangan akuisisi dua link Andi.

Perekaman CSI dari router ke ESP32-S3 sudah dicoba di kamar. Sudah ada rekaman saat kamar kosong, saat diam, dan saat berjalan. Sesi diam juga sudah dicoba di dua posisi untuk melihat perbedaan sinyal yang diterima. [Hasil dan grafik Log 6](docs/pilot-2026-11-18/README.md) · [Panduan akuisisi](docs/akuisisi.md)

## To do

- [x] **01. Menyiapkan pemeriksaan port di Windows.** Skrip [cek-port.ps1](scripts/cek-port.ps1) menampilkan port serial yang terlihat di Windows dan bisa memeriksa satu port berdasarkan namanya.
- [x] **02. Mengenali board yang akan dipakai.** ESP32-S3 N16R8 terbaca pada COM8. Router Wifi menjadi sumber paket untuk uji awal.
- [x] **03. Mencoba rekaman pertama di ruangan kosong.** Sebanyak 2.991 sampel tersimpan menggunakan contoh firmware Espressif.
- [x] **04. Membuat perekam CSI di laptop.** Perekam menyimpan keluaran serial, sampel CSI yang terbaca, dan catatan sesi di folder dengan ID unik.
  - [x] Perekam serial, pembacaan ulang berkas, metadata sesi, dan pemeriksaan format diuji di laptop.
  - [x] Jumlah sampel dan selang waktu antarsampel diperiksa pada rekaman awal. Firmware diagnostik juga sudah diuji untuk menyimpan CSI sebelum dan sesudah kompensasi dari paket yang sama.
- [ ] **05. Menyiapkan uji pendahuluan untuk eksperimen utama.**
  - [x] Rekam tiga kondisi awal di kamar dan bandingkan sesi diam pada dua posisi.
  - [ ] Susun rincian tata letak A sampai D, posisi perangkat, titik awal dan arah hadap, area gerak, daftar aktivitas, dan cara memberi label.
  - [ ] Tentukan cara mengecek kualitas rekaman dan siapkan prosedur keselamatan simulasi jatuh serta persetujuan peserta sesuai ketentuan yang berlaku sebelum sesi dengan peserta.
- [ ] **06. Mengumpulkan dan membagi rekaman.** Buat daftar rekaman yang memuat ID sesi, kode peserta, lingkungan, dan label. Rekaman atau sesi dibagi ke kelompok latih, validasi, dan uji sebelum dipotong menjadi jendela. Semua potongan dari satu rekaman harus tetap berada dalam kelompok yang sama.
- [ ] **07. Menyiapkan model awal.** Setelah jendela CSI terbentuk, hitung parameter normalisasi dari data latih yang sudah tersedia pada tahap tersebut. Model awal dilatih pada konfigurasi A. Konfigurasi, seed, dan checkpoint perlu disimpan supaya metode pembanding bisa dimulai dari titik yang sama.
- [ ] **08. Menguji model saat tata letak berubah.** Untuk RQ1, model statis dari A diuji pada setiap konfigurasi. Untuk RQ2 dan RQ3, naive fine-tuning dan Experience Replay dibandingkan dari checkpoint awal yang sama. Setelah belajar di B, model diuji di A dan B. Setelah C dan D, pengujian kembali mencakup semua lingkungan yang sudah dipelajari. Buffer replay hanya boleh berisi data latih yang sudah tersedia. Sebagai acuan offline, joint training menggunakan gabungan data latih A sampai D.
- [ ] **09. Menganalisis hasil untuk Bab 4.** Catat skor deteksi per lingkungan setelah setiap tahap agar perubahan kinerja di lingkungan lama terlihat. Retensi dan forgetting akan dihitung sesuai definisi yang dipilih. Untuk membandingkan biaya adaptasi, catat jumlah contoh dan ukuran buffer, RAM, waktu, jumlah pembaruan, serta jumlah contoh lama dan baru yang diproses. Setiap hasil perlu disertai konfigurasi dan versi kode yang digunakan.

ESP32-S3 N16R8 dan firmware diagnostik sudah dipakai untuk uji awal. Untuk eksperimen utama, konfigurasi akuisisi dan laju paket masih perlu ditetapkan bersama jumlah peserta, jumlah sesi, dan rincian tata letak. Panjang dan tumpang tindih jendela, arsitektur model, ukuran buffer, rasio replay, dan anggaran pelatihan juga masih terbuka.

## Cara memeriksa port ESP32 di Windows
1. Dengan board masih terlepas, jalankan skrip ini dan catat port yang muncul.

   ```powershell
   powershell -NoProfile -ExecutionPolicy RemoteSigned -File .\scripts\cek-port.ps1
   ```

2. Sambungkan board dengan kabel USB data, lalu ulangi perintah tadi. Kalau ada port baru, periksa namanya secara langsung. Ganti `COM5` pada contoh berikut dengan nama port yang muncul di komputer.

   ```powershell
   powershell -NoProfile -ExecutionPolicy RemoteSigned -File .\scripts\cek-port.ps1 -Port COM5
   $LASTEXITCODE
   ```

3. Cabut board dan ulangi pemeriksaan port tersebut. Jika port tersebut ikut hilang, kemungkinan besar itulah port yang dipakai board. Jika daftarnya tetap sama sepanjang pemeriksaan, cek kabel data, port USB, dan entri board di Device Manager untuk mengetahui driver yang sesuai.

Skrip menampilkan hasil dalam format JSON. Saat menampilkan seluruh daftar, kode keluar `0` berarti pemeriksaan berhasil, termasuk ketika daftarnya kosong. Saat memeriksa satu port, `0` berarti port ditemukan dan `1` berarti port tidak ditemukan. Kode `2` berarti Windows gagal membaca daftar port. Untuk mengecek apakah paket CSI sudah masuk, ikuti [panduan akuisisi](docs/akuisisi.md).

Rekaman mentah disimpan di `data/` dan keluaran percobaan di `runs/`. Kedua folder masuk `.gitignore`. Daftar rekaman menggunakan kode peserta.
