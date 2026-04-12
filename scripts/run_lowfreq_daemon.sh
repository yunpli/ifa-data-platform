#!/bin/zsh
set -euo pipefail
cd /Users/neoclaw/repos/ifa-data-platform
source .venv/bin/activate
export PYTHONPATH=/Users/neoclaw/repos/ifa-data-platform/src
exec python -m ifa_data_platform.lowfreq.daemon --loop
