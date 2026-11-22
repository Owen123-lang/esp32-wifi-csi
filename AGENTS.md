# Panduan kerja untuk agen

Repositori ini adalah basis pengembangan alat akuisisi Wi-Fi CSI bersama Andi dan Owen. Baca [Handover.md](Handover.md), [panduan akuisisi](docs/akuisisi.md), dan kode yang akan disentuh sebelum bekerja.

## Koordinasi perubahan

- Periksa branch, perubahan lokal, dan commit upstream sebelum mulai. Jaga perubahan yang sedang dikerjakan oleh Andi atau Owen.
- Jika ada perubahan upstream atau perbedaan antarsistem yang berdampak pada topologi, format serial, kualitas data, atau eksperimen, laporkan commit atau file terkait, dampak, dan usulan penyesuaiannya kepada Andi dan Owen. Tunggu kesepakatan sebelum mengubah bagian yang terdampak.
- Anggap router + 1 RX sebagai konfigurasi pilot yang terdokumentasi. Rancangan Andi memakai 1 TX + 2 RX ESP32-S3. Status keduanya sebagai konfigurasi yang akan didukung bersama masih perlu disepakati.
- Gunakan branch perubahan terpisah dan siapkan PR untuk ditinjau bersama ketika diminta. Jangan push atau membuka PR tanpa instruksi. Gunakan pesan commit yang jelas dalam bahasa Inggris.

## Firmware dan akuisisi

- Catat model board, commit firmware, versi ESP-IDF, konfigurasi radio, baud konsol, dan identitas build yang benar-benar dipasang. Simpan SSID, kata sandi, pemetaan COM lokal, data partisipan, rekaman serial mentah, dan build sementara di luar commit.
- Pertahankan alur `CSI_DATA`, `DIAM1`, dan `sampel.jsonl` selama kompatibilitasnya masih dibutuhkan oleh perekam. Bila format perlu berubah, sepakati cara membedakan versi dan perbarui parser serta pengujiannya bersama perubahan firmware.
- Pertahankan IQ sebelum kompensasi, panjang payload, indeks asli, timestamp perangkat, dan penanda bagian awal buffer yang tidak valid. Jangan mempertahankan pointer buffer milik driver setelah callback. Untuk pengembangan jalur akuisisi baru, salin data yang diperlukan di callback dan serialisasi di task terpisah.
- Untuk dua RX, gunakan identitas paket TX yang dapat ditelusuri di kedua link. Uji kecocokan CSI dengan marker di perangkat sebelum memakai hasil penyelarasan. Urutan callback maupun waktu kedatangan serial tidak dapat menggantikan identitas paket.
- Bedakan pemeriksaan source, tes parser, build, flash, dan uji radio fisik. Rekaman pilot tidak menetapkan laju efektif, parameter final, atau performa model untuk konfigurasi lain.

## Handover

Setelah perubahan substantif, perbarui [Handover.md](Handover.md) dengan tanggal, penanggung jawab, branch/commit, perubahan, verifikasi yang dilakukan, dan keputusan atau pekerjaan yang menunggu pihak lain.
