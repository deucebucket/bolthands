#!/bin/bash
# BoltHands 9B — Training launcher
# Usage: ./train.sh /path/to/dataset.jsonl
#
# Enters distrobox "ai", activates the unsloth venv, and runs
# unsloth train with the BoltHands config.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="${SCRIPT_DIR}/config.yaml"
VENV="source ~/ai-drive/ai-suite/unsloth-studio/bin/activate"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="${HOME}/ai-drive/bolthands/logs"

# ── Argument check ────────────────────────────────────────────
if [ -z "${1:-}" ]; then
    echo "Error: Dataset path required."
    echo "Usage: $0 /path/to/dataset.jsonl"
    exit 1
fi

DATASET="$1"

if [ ! -f "$DATASET" ]; then
    echo "Error: Dataset file not found: $DATASET"
    exit 1
fi

# ── Ensure log directory exists ───────────────────────────────
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/train_${TIMESTAMP}.log"

echo "=== BoltHands 9B Training ==="
echo "  Config:   ${CONFIG}"
echo "  Dataset:  ${DATASET}"
echo "  Log:      ${LOG_FILE}"
echo "  Started:  $(date -Iseconds)"
echo ""

# ── Run training inside distrobox ─────────────────────────────
distrobox enter ai -- bash -c "
    ${VENV}

    echo '[$(date -Iseconds)] Training started'

    unsloth train -c '${CONFIG}' --local-dataset '${DATASET}' 2>&1

    EXIT_CODE=\$?

    echo '[$(date -Iseconds)] Training finished with exit code \$EXIT_CODE'
    exit \$EXIT_CODE
" 2>&1 | tee "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}

echo ""
if [ "$EXIT_CODE" -eq 0 ]; then
    echo "[$(date -Iseconds)] Training completed successfully."
else
    echo "[$(date -Iseconds)] Training failed with exit code $EXIT_CODE."
    echo "Check log: $LOG_FILE"
fi

exit $EXIT_CODE
