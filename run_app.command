#!/bin/bash
set -euo pipefail
# always run from the repo this script lives in
cd "$(dirname "$0")"

# Ensure venv exists
if [[ ! -x "venv/bin/python" ]]; then
  /usr/bin/python3 -m venv venv
  ./venv/bin/pip install -r requirements.txt
fi

# Launch the GUI with your venv
exec ./venv/bin/python gui.py
