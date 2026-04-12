#!/bin/zsh
set -euo pipefail
cd /Users/neoclaw/repos/ifa-data-platform
source .venv/bin/activate
export PYTHONPATH=/Users/neoclaw/repos/ifa-data-platform/src
python scripts/lowfreq_monitor_report.py --send --target 1628724839 --account main
