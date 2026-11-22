#!/bin/sh
set -eu

run=$(mktemp -d /out/synthetic-XXXXXX)
python -m csi_tools simulate --config configs/pilot.example.json \
    --metadata configs/recording.example.json --output "$run/recording"
python -m csi_tools qc "$run/recording" > "$run/qc.json"
cat "$run/qc.json"
