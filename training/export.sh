#!/bin/bash
# BoltHands 9B — GGUF Export
# Usage: ./export.sh /path/to/checkpoint-dir output-name
#
# Exports a training checkpoint to GGUF Q4_K_M and Q5_K_M,
# then copies the resulting files to the models directory.
set -euo pipefail

VENV="source ~/ai-drive/ai-suite/unsloth-studio/bin/activate"
MODELS_DIR="${HOME}/ai-drive/ai-suite/models"
EXPORT_BASE="${HOME}/ai-drive/bolthands/exports"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

# ── Argument check ────────────────────────────────────────────
if [ -z "${1:-}" ] || [ -z "${2:-}" ]; then
    echo "Error: Checkpoint directory and output name required."
    echo "Usage: $0 /path/to/checkpoint-dir bolthands-9b-v1"
    exit 1
fi

CHECKPOINT="$1"
OUTPUT_NAME="$2"
EXPORT_DIR="${EXPORT_BASE}/${OUTPUT_NAME}_${TIMESTAMP}"

echo "=== BoltHands 9B GGUF Export ==="
echo "  Checkpoint:  ${CHECKPOINT}"
echo "  Output name: ${OUTPUT_NAME}"
echo "  Export dir:  ${EXPORT_DIR}"
echo "  Models dir:  ${MODELS_DIR}"
echo "  Started:     $(date -Iseconds)"
echo ""

# ── Export inside distrobox ───────────────────────────────────
distrobox enter ai -- bash -c "
    ${VENV}

    mkdir -p '${EXPORT_DIR}'

    echo '=== Exporting Q4_K_M ==='
    unsloth export '${CHECKPOINT}' '${EXPORT_DIR}/q4_k_m' \
        --format gguf --quantization q4_k_m

    echo ''
    echo '=== Exporting Q5_K_M ==='
    unsloth export '${CHECKPOINT}' '${EXPORT_DIR}/q5_k_m' \
        --format gguf --quantization q5_k_m

    echo ''
    echo 'Export complete.'
"

EXIT_CODE=$?
if [ "$EXIT_CODE" -ne 0 ]; then
    echo "[$(date -Iseconds)] Export failed with exit code $EXIT_CODE."
    exit $EXIT_CODE
fi

# ── Copy to models directory ─────────────────────────────────
echo ""
echo "=== Copying to models directory ==="
mkdir -p "$MODELS_DIR"

# Find and copy the GGUF files
for quant_dir in "${EXPORT_DIR}/q4_k_m" "${EXPORT_DIR}/q5_k_m"; do
    if [ -d "$quant_dir" ]; then
        for gguf_file in "${quant_dir}"/*.gguf; do
            if [ -f "$gguf_file" ]; then
                dest="${MODELS_DIR}/$(basename "$gguf_file")"
                echo "  Copying: $(basename "$gguf_file") -> ${MODELS_DIR}/"
                cp "$gguf_file" "$dest"
            fi
        done
    fi
done

echo ""
echo "[$(date -Iseconds)] Export and copy completed successfully."
echo "  Q4_K_M: ${EXPORT_DIR}/q4_k_m/"
echo "  Q5_K_M: ${EXPORT_DIR}/q5_k_m/"
echo "  Models: ${MODELS_DIR}/"
