# Eksperimen deteksi jatuh dengan Wi-Fi CSI dan ESP32
## To do

Pada uji ulang sesi diam, 2.660 paket diperiksa sebelum dan sesudah kompensasi. Sebagian komponen CSI berubah menjadi nol, tetapi setiap paket masih menyimpan komponen yang bernilai. [Hasil uji ulang dan grafik Log 6](docs/pilot-2026-11-18/README.md)

ESP32-S3 sudah dipakai untuk merekam tiga kondisi di kamar. Pada sesi diam, sebagian besar sampel berisi nol di seluruh komponen CSI. Penyebabnya masih diperiksa sebelum pengambilan data berikutnya. [Hasil dan grafik uji awal](docs/pilot-2026-11-17/README.md) · [Panduan akuisisi](docs/akuisisi.md)

- [x] **01. Menyiapkan pemeriksaan port di Windows.** Skrip [cek-port.ps1](scripts/cek-port.ps1) menampilkan port serial yang terlihat di Windows dan bisa memeriksa satu port berdasarkan namanya.
- [x] **02. Mengenali board yang akan dipakai.** ESP32-S3 N16R8 terbaca pada COM8. Router Wifi menjadi sumber paket untuk uji awal.
- [x] **03. Mencoba rekaman pertama di ruangan kosong.** Sebanyak 2.991 sampel tersimpan menggunakan contoh firmware Espressif.
- [ ] **04. Membuat perekam CSI di laptop.** Setiap berkas mentah perlu punya ID rekaman, ID sesi, konfigurasi ruangan, dan waktu perekaman. Periksa jumlah paket, jumlah sampel CSI yang valid, serta selang waktu antarsampel. Jika sambungan putus di tengah sesi, rekamannya tetap harus bisa ditelusuri.
  - [x] Perekam serial, pembacaan ulang berkas, metadata sesi, dan pemeriksaan format diuji di laptop.
  - [x] Kualitas rekaman dan selang waktu antarsampel diperiksa pada tiga sesi. Asal nilai nol pada keluaran firmware masih perlu ditelusuri.
- [ ] **05. Menyiapkan dan menjalankan uji pendahuluan.** Dokumentasikan tata letak A sampai D, posisi perangkat, area gerak, aktivitas, dan cara memberi label. Sebelum melibatkan peserta, pastikan prosedur keselamatan simulasi jatuh dan persetujuan peserta sesuai ketentuan yang berlaku. Hasil uji pendahuluan digunakan untuk menilai apakah kualitas rekaman memadai untuk eksperimen utama.
- [ ] **06. Mengumpulkan dan membagi rekaman.** Buat daftar rekaman yang memuat ID sesi, kode peserta, lingkungan, dan label. Rekaman atau sesi dibagi ke kelompok latih, validasi, dan uji sebelum dipotong menjadi jendela. Semua potongan dari satu rekaman harus tetap berada dalam kelompok yang sama.
- [ ] **07. Menyiapkan model awal.** Setelah jendela CSI terbentuk, hitung parameter normalisasi dari data latih yang sudah tersedia pada tahap tersebut. Model awal dilatih pada konfigurasi A. Konfigurasi, seed, dan checkpoint perlu disimpan supaya metode pembanding bisa dimulai dari titik yang sama.
- [ ] **08. Menguji model saat tata letak berubah.** Untuk RQ1, model statis dari A diuji pada setiap konfigurasi. Untuk RQ2 dan RQ3, naive fine-tuning dan Experience Replay dibandingkan dari checkpoint awal yang sama. Setelah belajar di B, model diuji di A dan B. Setelah C dan D, pengujian kembali mencakup semua lingkungan yang sudah dipelajari. Buffer replay hanya boleh berisi data latih yang sudah tersedia. Sebagai acuan offline, joint training menggunakan gabungan data latih A sampai D.
- [ ] **09. Menganalisis hasil untuk Bab 4.** Catat skor deteksi per lingkungan setelah setiap tahap agar perubahan kinerja di lingkungan lama terlihat. Retensi dan forgetting akan dihitung sesuai definisi yang dipilih. Untuk membandingkan biaya adaptasi, catat jumlah contoh dan ukuran buffer, RAM, waktu, jumlah pembaruan, serta jumlah contoh lama dan baru yang diproses. Setiap hasil perlu disertai konfigurasi dan versi kode yang digunakan.

Varian board, firmware, jumlah peserta dan sesi, rincian perubahan tata letak, serta laju paket masih perlu ditentukan. Pilihan panjang dan tumpang tindih jendela, arsitektur model, ukuran buffer, rasio replay, dan anggaran pelatihan juga masih terbuka.

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

Skrip menampilkan hasil dalam format JSON. Saat menampilkan seluruh daftar, kode keluar `0` berarti pemeriksaan berhasil, termasuk ketika daftarnya kosong. Saat memeriksa satu port, `0` berarti port ditemukan dan `1` berarti port tidak ditemukan. Kode `2` berarti Windows gagal membaca daftar port. Penerimaan CSI akan diperiksa melalui isi rekaman pada langkah 03.

Rekaman mentah disimpan di `data/` dan keluaran percobaan di `runs/`. Kedua folder masuk `.gitignore`. Daftar rekaman menggunakan kode peserta.
