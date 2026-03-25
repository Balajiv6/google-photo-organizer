#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# startup.sh — launch google-photos-organizer (Linux / macOS / WSL / CI)
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# --------------------------------------------------------------------------- #
# Activate virtual environment if one exists
# --------------------------------------------------------------------------- #
for venv_dir in venv .venv; do
    activate="$SCRIPT_DIR/$venv_dir/bin/activate"
    if [ -f "$activate" ]; then
        # shellcheck source=/dev/null
        source "$activate"
        echo "[startup] Activated virtual environment: $venv_dir"
        break
    fi
done

# --------------------------------------------------------------------------- #
# Ensure dependencies are installed
# --------------------------------------------------------------------------- #
pip install -q -r "$SCRIPT_DIR/requirements.txt"

# --------------------------------------------------------------------------- #
# Run the organiser
# Pass-through any extra arguments, e.g. env-var overrides:
#   ORGANIZER_DRY_RUN=false ./startup.sh
# --------------------------------------------------------------------------- #
echo "[startup] Starting google-photos-organizer …"
PYTHONPATH="$SCRIPT_DIR/src" python "$SCRIPT_DIR/src/main.py" "$@"
