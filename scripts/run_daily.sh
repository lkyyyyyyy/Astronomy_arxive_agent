#!/bin/zsh
set -euo pipefail

PROJECT_DIR="/Users/lky/Desktop/Agent/arxive_agent"
PYTHON="/opt/anaconda3/bin/python3"

cd "$PROJECT_DIR"
mkdir -p logs

"$PYTHON" main.py --config config/config.yaml >> logs/launchd.log 2>&1

