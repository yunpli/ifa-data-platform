#!/bin/zsh
set -euo pipefail

REPO_DIR="/Users/neoclaw/repos/ifa-data-platform"
VENV_PY="$REPO_DIR/.venv/bin/python"
OUT_DIR="$REPO_DIR/artifacts/runtime_reports"
mkdir -p "$OUT_DIR"
STAMP=$(date +%F_%H%M)
OUT_FILE="$OUT_DIR/runtime_24h_report_${STAMP}.txt"

cd "$REPO_DIR"
"$VENV_PY" scripts/runtime_24h_report.py --hours 24 --out "$OUT_FILE"
echo "$OUT_FILE"
