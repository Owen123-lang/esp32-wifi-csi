#!/usr/bin/env bash
set -euo pipefail

role=${1:-tx}
case "$role" in
    tx|rx-a|rx-b) ;;
    *) printf 'Unknown role: %s (use tx, rx-a, or rx-b)\n' "$role" >&2; exit 2 ;;
esac
flash="/out/firmware/$role/qemu-flash.bin"
if [[ ! -f "$flash" ]]; then
    printf 'Build %s first with: docker compose run --rm firmware %s\n' "$role" "$role" >&2
    exit 2
fi

run=$(mktemp -d "/out/qemu-$role-XXXXXX")
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cp "$flash" "$work/flash.bin"
status=0
timeout --kill-after=5s 25s qemu-system-xtensa -display none -monitor none \
    -machine esp32s3 -nic none -serial "file:$run/uart.log" \
    -drive "file=$work/flash.bin,if=mtd,format=raw" > "$run/qemu.log" 2>&1 || status=$?
printf '%s\n' "$status" > "$run/exit-status.txt"
printf 'QEMU logs: %s\n' "$run"
case "$status" in
    0|124) ;;
    *) tail -n 25 "$run/qemu.log" >&2; exit "$status" ;;
esac
tail -n 25 "$run/uart.log"
grep -q 'ESP-ROM:esp32s3' "$run/uart.log"
