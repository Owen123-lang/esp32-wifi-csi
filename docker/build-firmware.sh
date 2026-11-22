#!/usr/bin/env bash
set -euo pipefail

if (( $# == 0 )); then
    set -- tx rx-a rx-b
fi
for role in "$@"; do
    case "$role" in
        tx|rx-a|rx-b) ;;
        *) printf 'Unknown role: %s (use tx, rx-a, or rx-b)\n' "$role" >&2; exit 2 ;;
    esac
done

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
for role in "$@"; do
    destination="/out/firmware/$role"
    mkdir -p "$destination"
    idf.py -B "$work/build-$role" \
        -D IDF_TARGET=esp32s3 \
        -D "SDKCONFIG=$work/sdkconfig.$role" \
        -D "SDKCONFIG_DEFAULTS=sdkconfig.defaults;profiles/$role.defaults" \
        build 2>&1 | tee "$destination/build.log"
    grep -Fx "CONFIG_CSI_DEVICE_ID=\"$role\"" "$work/sdkconfig.$role"

    (
        cd "$work/build-$role"
        python -m esptool --chip esp32s3 merge_bin --fill-flash-size 4MB -o qemu-flash.bin @flash_args
        install -D -m 0644 bootloader/bootloader.bin "$destination/bootloader/bootloader.bin"
        install -D -m 0644 partition_table/partition-table.bin "$destination/partition_table/partition-table.bin"
        install -m 0644 skripsi_csi_pilot.bin skripsi_csi_pilot.elf qemu-flash.bin flash_args "$destination/"
    )
    install -m 0644 "$work/sdkconfig.$role" "$destination/sdkconfig"
    (
        cd "$destination"
        sha256sum skripsi_csi_pilot.bin qemu-flash.bin > SHA256SUMS
    )
    printf 'Built ESP32-S3 %s in %s\n' "$role" "$destination"
done
