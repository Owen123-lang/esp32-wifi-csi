# Eksperimen deteksi jatuh dengan Wi-Fi CSI dan ESP32

Repositori kerja Rowen dan Alvin untuk eksperimen skripsi. ESP32 merekam CSI. Laptop atau PC mengolah rekaman, melatih model, menjalankan adaptasi, dan mengukur kinerjanya. Pertanyaan eksperimennya adalah apakah model dapat mengenali jatuh ketika tata letak ruangan berubah, seberapa baik kemampuannya bertahan di lingkungan lama, dan berapa tambahan memori serta waktu yang dibutuhkan oleh Experience Replay.

## Roadmap

Centang setiap langkah setelah bukti pada baris tersebut tersedia. Tahap awal dapat dikerjakan tanpa peserta.

- [x] **01. Buat alat pemeriksa port serial untuk Windows.** Skrip di `scripts/cek-port.ps1` menampilkan daftar port dan dapat memeriksa satu port pilihan. Cara menjalankannya ada di bawah.
- [ ] **02. Kenali perangkat di meja.** Catat model yang tercetak pada board, port yang muncul saat board disambungkan, dan sumber paket Wi-Fi yang tersedia. Pastikan port yang sama hilang saat board dilepas.
- [ ] **03. Buktikan alur akuisisi.** Pilih contoh akuisisi dan versi firmware yang cocok dengan board. Rekam satu sesi teknis di ruangan kosong. Periksa bahwa keluaran berisi nilai CSI yang dapat dibaca. Simpan versi firmware, konfigurasi Wi-Fi, peran pengirim dan penerima, serta satuan waktu.
- [ ] **04. Buat perekam dan pemeriksa kualitas di host.** Simpan data mentah beserta ID rekaman, ID sesi, konfigurasi ruangan, dan waktu. Tampilkan jumlah paket diterima, jumlah sampel CSI valid, serta distribusi selang waktu antarsampel. Uji bahwa rekaman yang terputus tetap dapat ditelusuri.
- [ ] **05. Siapkan protokol dan jalankan pilot.** Dokumentasikan tata letak A sampai D, posisi perangkat, area gerak, prosedur aktivitas, dan aturan anotasi. Sebelum merekam peserta, pastikan prosedur keselamatan simulasi jatuh dan persetujuan peserta sesuai ketentuan yang berlaku. Gunakan pilot untuk menilai kelayakan akuisisi dan memperjelas parameter.
- [ ] **06. Kumpulkan dan bagi rekaman.** Buat manifest yang menghubungkan setiap rekaman dengan sesi, peserta berkode, lingkungan, dan label. Pisahkan data latih, validasi, dan uji pada tingkat rekaman atau sesi sebelum membentuk jendela. Periksa bahwa turunan rekaman yang sama selalu berada dalam satu kelompok.
- [ ] **07. Siapkan prapemrosesan dan model awal.** Bentuk jendela CSI dan hitung parameter normalisasi hanya dari data latih yang tersedia pada tahap itu. Latih model pada A dan simpan konfigurasi, seed, serta checkpoint awal untuk semua pembanding.
- [ ] **08. Uji pengaruh lingkungan dan adaptasi.** Untuk RQ1, uji model statis dari A pada tiap konfigurasi. Untuk RQ2 dan RQ3, jalankan naive fine-tuning dan Experience Replay dari checkpoint awal yang sama. Setelah adaptasi pada B, uji A dan B. Ulangi pada C dan D dengan menguji seluruh lingkungan yang sudah dipelajari. Isi buffer hanya dengan data latih yang sudah tersedia. Jalankan joint training sebagai acuan offline dengan akses ke gabungan data latih A sampai D.
- [ ] **09. Susun analisis Bab 4.** Simpan skor deteksi per lingkungan dan tahap, lalu hitung retensi dan forgetting sesuai definisi yang disepakati. Laporkan jumlah serta ukuran sampel buffer, RAM, waktu adaptasi, jumlah pembaruan, dan paparan contoh lama maupun baru. Sertakan konfigurasi dan versi kode untuk setiap hasil.

**Keputusan yang masih terbuka.** Varian board dan firmware, jumlah peserta dan sesi, perubahan tata letak, laju paket, panjang dan tumpang tindih jendela, arsitektur model, ukuran buffer, rasio replay, dan anggaran perbandingan akan ditentukan berdasarkan perangkat, pilot, dan keputusan penelitian.

## Mulai dari pemeriksaan port (Windows)

Dari PowerShell, buka folder repositori. Pada komputer baru, ambil salinannya terlebih dahulu.

```powershell
git clone https://github.com/Owen123-lang/esp32-wifi-csi.git
cd esp32-wifi-csi
```

1. Lepaskan board dan jalankan perintah berikut. Catat daftar port awal.

   ```powershell
   powershell -NoProfile -ExecutionPolicy RemoteSigned -File .\scripts\cek-port.ps1
   ```

2. Sambungkan board dengan kabel USB data dan ulangi perintah yang sama. Jika muncul port baru, periksa port itu secara eksplisit. Ganti `COM5` dengan nama yang terlihat di komputer.

   ```powershell
   powershell -NoProfile -ExecutionPolicy RemoteSigned -File .\scripts\cek-port.ps1 -Port COM5
   $LASTEXITCODE
   ```

3. Lepaskan board dan ulangi pemeriksaan port pilihan. Port yang muncul saat disambungkan dan hilang saat dilepas adalah kandidat port board. Jika daftar tetap sama, periksa kabel data, port USB, dan entri perangkat di Device Manager sebelum memilih driver yang sesuai dengan board.

Keluaran berbentuk JSON. Pemeriksaan daftar berhasil dengan kode `0`, termasuk jika daftar kosong. Untuk pemeriksaan satu port, kode `0` berarti port ditemukan dan `1` berarti port tidak ditemukan. Kode `2` menunjukkan Windows gagal membaca daftar port. Skrip hanya memeriksa nama port yang terlihat oleh Windows. Pengujian firmware dan penerimaan CSI dilakukan pada langkah 03.

Simpan rekaman lokal di `data/` dan keluaran percobaan di `runs/`. Kedua folder dikecualikan dari Git. Gunakan ID peserta berkode pada manifest penelitian.
