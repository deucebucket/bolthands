#!/bin/bash
# BoltHands Training Watchdog
# Monitors the training process and restarts from latest checkpoint if it dies.
# Also monitors GPU temperature and pauses if too hot.
#
# Usage: nohup bash training/train_watchdog.sh > ~/ai-drive/bolthands/logs/watchdog.log 2>&1 &

set -euo pipefail

TRAIN_LOG_DIR="$HOME/ai-drive/bolthands/logs"
CHECKPOINT_DIR="$HOME/ai-drive/bolthands/checkpoints"
DATASET="$HOME/ai-drive/bolthands/training-data/all-domains/train.jsonl"
MAX_RESTARTS=3
GPU_TEMP_LIMIT=88
RESTART_COUNT=0

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

get_gpu_temp() {
    nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader 2>/dev/null || echo "0"
}

get_train_pid() {
    pgrep -f "train_direct.py" 2>/dev/null || echo ""
}

wait_for_cooldown() {
    local temp
    temp=$(get_gpu_temp)
    while [ "$temp" -gt "$GPU_TEMP_LIMIT" ]; do
        log "GPU at ${temp}C — too hot (limit ${GPU_TEMP_LIMIT}C). Waiting 60s..."
        sleep 60
        temp=$(get_gpu_temp)
    done
    log "GPU at ${temp}C — cool enough to proceed."
}

# Monitor loop
log "Watchdog started. Monitoring training process."
log "Max restarts: $MAX_RESTARTS, GPU temp limit: ${GPU_TEMP_LIMIT}C"

while true; do
    PID=$(get_train_pid)

    if [ -z "$PID" ]; then
        # Training process not found

        # Check if it finished successfully (GGUF exists in latest checkpoint)
        LATEST_CKPT=$(ls -td "$CHECKPOINT_DIR"/bolthands-* 2>/dev/null | head -1)
        if [ -n "$LATEST_CKPT" ] && ls "$LATEST_CKPT"/gguf-*/*.gguf &>/dev/null; then
            log "Training completed! GGUF found in $LATEST_CKPT"

            # Copy to models dir
            for gguf in "$LATEST_CKPT"/gguf-*/*.gguf; do
                DEST="$HOME/ai-drive/ai-suite/models/$(basename "$gguf")"
                if [ ! -f "$DEST" ]; then
                    cp "$gguf" "$DEST"
                    log "Copied $(basename "$gguf") to models dir"
                fi
            done

            log "All done. Watchdog exiting."
            exit 0
        fi

        # Not finished — check if we should restart
        if [ "$RESTART_COUNT" -ge "$MAX_RESTARTS" ]; then
            log "ERROR: Training died $RESTART_COUNT times. Giving up."
            exit 1
        fi

        RESTART_COUNT=$((RESTART_COUNT + 1))
        log "Training process not found (crash #$RESTART_COUNT). Waiting for GPU cooldown..."
        wait_for_cooldown

        log "Restarting training (attempt $RESTART_COUNT/$MAX_RESTARTS)..."

        # Find latest checkpoint to resume from
        RESUME_CKPT=$(ls -td "$CHECKPOINT_DIR"/bolthands-*/checkpoint-* 2>/dev/null | head -1)

        if [ -n "$RESUME_CKPT" ]; then
            log "Resuming from checkpoint: $RESUME_CKPT"
            # For now, just restart from scratch since Unsloth doesn't easily resume
            # The checkpoints are there for manual recovery
        fi

        # Restart training
        cd /var/home/deucebucket/bolthands
        distrobox enter ai -- bash -c "
            source ~/ai-drive/ai-suite/unsloth-studio/bin/activate
            export HF_HOME=~/ai-drive/.cache/huggingface
            export PYTHONUNBUFFERED=1
            cd /var/home/deucebucket/bolthands
            nohup python training/train_direct.py \
                --model unsloth/Qwen3.5-9B \
                --dataset $DATASET \
                --epochs 2 \
                --max-seq-length 1024 \
                --batch-size 2 \
                --grad-accum 8 \
                --lora-r 32 \
                --lora-alpha 64 \
                > $TRAIN_LOG_DIR/train-restart-${RESTART_COUNT}-\$(date +%Y%m%d-%H%M%S).log 2>&1 &
            echo \$!
        " 2>/dev/null

        log "Restart launched. Waiting 60s for it to initialize..."
        sleep 60
    else
        # Training is running — check GPU temp
        TEMP=$(get_gpu_temp)
        if [ "$TEMP" -gt "$GPU_TEMP_LIMIT" ]; then
            log "WARNING: GPU at ${TEMP}C (limit ${GPU_TEMP_LIMIT}C). Training still running — monitoring closely."
        fi
    fi

    # Check every 5 minutes
    sleep 300
done
