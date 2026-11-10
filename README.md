# Eksperimen deteksi jatuh dengan Wi-Fi CSI dan ESP32

Saya menyiapkan repositori ini bersama Alvin untuk bagian eksperimen skripsi saya. Saya ingin tahu apakah model masih bisa mengenali orang jatuh setelah tata letak benda di ruangan berubah. Untuk mengujinya, saya akan menggunakan ESP32 untuk merekam Channel State Information (CSI) dan laptop atau PC untuk mengolah rekaman serta melatih model.

Saya juga ingin melihat apa yang terjadi setelah model belajar dari tata letak baru. Apakah model masih mengenali jatuh pada tata letak sebelumnya? Di bagian ini saya akan menguji Experience Replay, lalu mengukur berapa tambahan memori dan waktu yang dibutuhkan untuk adaptasi.

## Rencana kerja

Saat ini baru skrip pemeriksa port yang siap. Langkah kami berikutnya adalah menyambungkan board dan mengenali port yang dipakainya.

- [x] **01. Menyiapkan pemeriksaan port di Windows.** Skrip [cek-port.ps1](scripts/cek-port.ps1) menampilkan port serial yang terlihat di Windows dan bisa memeriksa satu port berdasarkan namanya.
- [ ] **02. Mengenali board yang akan dipakai.** Kami akan mencatat model yang tertulis pada board, port yang muncul saat kabel USB dipasang, dan perangkat yang tersedia sebagai sumber paket Wi-Fi.
- [ ] **03. Mencoba rekaman pertama di ruangan kosong.** Setelah tahu model board, kami bisa memilih contoh akuisisi dan firmware yang sesuai. Targetnya satu rekaman berisi nilai CSI yang bisa dibaca. Catatan sesi mencakup versi firmware, pengaturan Wi-Fi, perangkat pengirim dan penerima, serta satuan waktu.
- [ ] **04. Membuat perekam CSI di laptop.** Setiap berkas mentah perlu punya ID rekaman, ID sesi, konfigurasi ruangan, dan waktu perekaman. Kami akan memeriksa jumlah paket, jumlah sampel CSI yang valid, serta selang waktu antarsampel. Jika sambungan putus di tengah sesi, rekamannya tetap harus bisa ditelusuri.
- [ ] **05. Menyiapkan dan menjalankan uji pendahuluan.** Saya akan mendokumentasikan tata letak A sampai D, posisi perangkat, area gerak, aktivitas, dan cara memberi label. Sebelum melibatkan peserta, saya perlu memastikan prosedur simulasi jatuh dan persetujuan peserta sesuai ketentuan yang berlaku. Dari uji ini saya ingin tahu apakah rekamannya cukup baik untuk eksperimen utama.
- [ ] **06. Mengumpulkan dan membagi rekaman.** Saya akan membuat daftar rekaman yang memuat ID sesi, kode peserta, lingkungan, dan label. Rekaman atau sesi dibagi ke kelompok latih, validasi, dan uji sebelum dipotong menjadi jendela. Semua potongan dari satu rekaman harus tetap berada dalam kelompok yang sama.
- [ ] **07. Menyiapkan model awal.** Setelah membentuk jendela CSI, saya akan menghitung parameter normalisasi dari data latih yang sudah tersedia pada tahap tersebut. Model awal dilatih pada konfigurasi A. Konfigurasi, seed, dan checkpoint perlu disimpan supaya metode pembanding bisa dimulai dari titik yang sama.
- [ ] **08. Menguji model saat tata letak berubah.** Untuk RQ1, saya akan menguji model statis dari A pada setiap konfigurasi. Untuk RQ2 dan RQ3, saya akan membandingkan naive fine-tuning dan Experience Replay dari checkpoint awal yang sama. Setelah belajar di B, model diuji di A dan B. Setelah C dan D, pengujian kembali mencakup semua lingkungan yang sudah dipelajari. Buffer replay hanya boleh berisi data latih yang sudah tersedia. Sebagai acuan offline, joint training menggunakan gabungan data latih A sampai D.
- [ ] **09. Menganalisis hasil untuk Bab 4.** Saya akan mencatat skor deteksi per lingkungan setelah setiap tahap agar perubahan kinerja di lingkungan lama terlihat. Retensi dan forgetting akan dihitung sesuai definisi yang dipilih. Untuk membandingkan biaya adaptasi, saya akan mencatat jumlah contoh dan ukuran buffer, RAM, waktu, jumlah pembaruan, serta jumlah contoh lama dan baru yang diproses. Setiap hasil perlu disertai konfigurasi dan versi kode yang digunakan.

Saya masih perlu menentukan varian board, firmware, jumlah peserta dan sesi, rincian perubahan tata letak, serta laju paket. Pilihan panjang dan tumpang tindih jendela, arsitektur model, ukuran buffer, rasio replay, dan anggaran pelatihan juga masih terbuka.

## Cara kami mengecek port ESP32 di Windows

Di komputer yang belum punya salinan repo, mulai dari PowerShell dengan perintah berikut.

```powershell
git clone https://github.com/Owen123-lang/esp32-wifi-csi.git
cd esp32-wifi-csi
```

1. Dengan board masih terlepas, jalankan skrip ini dan catat port yang muncul.

   ```powershell
   powershell -NoProfile -ExecutionPolicy RemoteSigned -File .\scripts\cek-port.ps1
   ```

2. Sambungkan board dengan kabel USB data, lalu ulangi perintah tadi. Kalau ada port baru, periksa namanya secara langsung. Di contoh ini saya memakai `COM5`. Ganti dengan port yang muncul di komputer.

   ```powershell
   powershell -NoProfile -ExecutionPolicy RemoteSigned -File .\scripts\cek-port.ps1 -Port COM5
   $LASTEXITCODE
   ```

3. Cabut board dan ulangi pemeriksaan port tersebut. Jika port ikut hilang, kita sudah punya petunjuk port mana yang dipakai board. Jika daftarnya tetap sama sepanjang pemeriksaan, cek kabel data, port USB, dan entri board di Device Manager untuk mengetahui driver yang sesuai.

Skrip menampilkan hasil dalam format JSON. Saat menampilkan seluruh daftar, kode keluar `0` berarti pemeriksaan berhasil, termasuk ketika daftarnya kosong. Saat memeriksa satu port, `0` berarti port ditemukan dan `1` berarti port tidak ditemukan. Kode `2` berarti Windows gagal membaca daftar port. Untuk memastikan CSI benar-benar diterima, kami akan memeriksa isi rekaman pada langkah 03.

Rekaman mentah disimpan di `data/` dan keluaran percobaan di `runs/`. Kedua folder masuk `.gitignore`. Daftar rekaman menggunakan kode peserta.
