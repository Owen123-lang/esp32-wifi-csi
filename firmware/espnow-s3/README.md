# ESP32-S3 pilot firmware

Target eksplisit: **ESP-IDF v5.4.3**, **ESP32-S3**, radio 2.4 GHz HT20/MCS0, kanal awal 6, nominal 100 pengiriman/detik, console UART 921600 baud. Angka ini pilihan pilot, bukan parameter eksperimen final. Source menolak target/versi IDF lain agar perubahan ABI tidak lolos diam-diam.

## Profil perangkat

| Profil | ID | MAC lokal | Fungsi |
|---|---|---|---|
| tx | tx | 02:00:00:00:00:01 | Broadcast ESP-NOW berisi boot ID, sequence, timestamp TX |
| rx-a | rx-a | 02:00:00:00:00:02 | CSI dan marker dari TX yang ditentukan |
| rx-b | rx-b | 02:00:00:00:00:03 | Sama, geometri pengamatan berbeda |

Gunakan hanya satu set identitas ini pada lokasi pilot. Tidak menghubungkan board ke access point atau menyimpan password Wi-Fi. Log marker dan CSI dipasangkan di host dengan timestamp RX lalu kedua link dipasangkan memakai identitas paket TX. Tidak menganggap timestamp kedatangan serial sebagai waktu RF.

## Build dan flash

Pasang ESP-IDF v5.4.3 melalui petunjuk resmi Espressif dan buka terminal dengan environment IDF aktif. Dari root repository:

```powershell
./firmware/espnow-s3/build.ps1 -Role tx
./firmware/espnow-s3/build.ps1 -Role rx-a
./firmware/espnow-s3/build.ps1 -Role rx-b
```

Hanya setelah memilih COM board yang benar, jalankan secara eksplisit:

```powershell
./firmware/espnow-s3/build.ps1 -Role tx -Port COM5 -Flash
./firmware/espnow-s3/build.ps1 -Role rx-a -Port COM6 -Flash
./firmware/espnow-s3/build.ps1 -Role rx-b -Port COM7 -Flash
```

COM di atas contoh. Script tidak memilih board atau melakukan erase-flash otomatis. Rutinitas inisialisasi NVS mengikuti penanganan no-free-pages/version IDF; cadangkan konfigurasi board jika sebelumnya dipakai untuk proyek lain. Serial collector menggunakan UART console, bukan asumsi USB native serial/JTAG; periksa jenis bridge/pin board dan menuconfig sebelum flash.

Build Linux dari `firmware/espnow-s3`:

```sh
idf.py -B build-tx -D IDF_TARGET=esp32s3 -D SDKCONFIG=sdkconfig.tx -D 'SDKCONFIG_DEFAULTS=sdkconfig.defaults;profiles/tx.defaults' build
```

Ganti tx dengan rx-a/rx-b. Profil memakai build directory dan sdkconfig terpisah supaya konfigurasi role tidak tertukar. Setelah mengubah defaults, periksa konfigurasi yang dihasilkan; sdkconfig lama tidak otomatis mengikuti semua perubahan default. Log BOOT mencantumkan identitas, IDF dan konfigurasi radio.

Script PowerShell juga memeriksa identitas pada sdkconfig hasil build dan menulis `build-{role}/flash-manifest.json`: role, versi IDF, commit, checksum aplikasi/config/source, serta apakah flash melalui script berhasil. Simpan manifest ini bersama inventaris eksperimen lokal. Status flashed tidak membuktikan penerimaan RF dan tidak mendeteksi flash manual di luar script.

## Akuisisi

Callback CSI menyalin data dan metadata ke antrean; serialisasi dilakukan oleh task logger. IQ tetap signed 8-bit, urutan imaginary/real sesuai SDK. Empat byte pertama tetap disimpan dan ditandai lewat first_word_invalid. HT-LTF/STBC tidak diaktifkan: host mensyaratkan panjang LLTF 128 byte untuk format pilot ini.

Frame aplikasi tidak dibaca dari offset payload CSI privat. Marker diterima melalui API ESP-NOW yang terdokumentasi. Pencocokan timestamp kedua callback harus diuji pada hardware; bila tidak sesuai, recording tidak menghasilkan window, bukan digabung berdasarkan urutan callback. Queue-drop counter mencakup event CSI/marker yang gagal masuk antrean; itu bukan metrik kehilangan radio murni.

Source awal untuk ketiga profil lulus CI di repo skripsi Andi. Status build di repo ini dan hasil pilot fisik dicatat di [Handover.md](../../Handover.md). Panduan capture dan QC tersedia di [espnow/README.md](../../espnow/README.md).

## Sumber primer API

- [ESP-IDF v5.4.3 ESP32-S3 CSI](https://docs.espressif.com/projects/esp-idf/en/v5.4.3/esp32s3/api-guides/wifi.html#wi-fi-channel-state-information)
- [Header CSI v5.4.3](https://github.com/espressif/esp-idf/blob/v5.4.3/components/esp_wifi/include/local/esp_wifi_types_native.h)
- [Header ESP-NOW v5.4.3](https://github.com/espressif/esp-idf/blob/v5.4.3/components/esp_wifi/include/esp_now.h)
