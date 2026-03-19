# Unsloth CLI & Python API Training Research

**Date:** 2026-03-18
**Version installed:** unsloth 2026.3.7
**Venv:** ~/ai-drive/ai-suite/unsloth-studio/
**Hardware:** RTX 3090 24GB, distrobox "ai" (CUDA 12.6)

---

## 1. CLI Subcommands

The `unsloth` CLI has full training support beyond just `unsloth studio`. All commands available:

```
unsloth train             # Launch headless training (no UI required)
unsloth inference         # Run single inference on a model
unsloth export            # Export checkpoint to GGUF, merged, or LoRA
unsloth list-checkpoints  # List training checkpoints in outputs dir
unsloth ui                # Alias for 'unsloth studio'
unsloth studio            # Launch web UI server
unsloth studio setup      # One-time studio environment setup
unsloth studio reset-password
```

### unsloth train

Full CLI training with every parameter exposed as flags OR via YAML/JSON config:

```bash
# Activate the venv first (inside distrobox "ai")
source ~/ai-drive/ai-suite/unsloth-studio/bin/activate

# Minimal example - all flags
unsloth train \
  --model "unsloth/Qwen3.5-9B" \
  --dataset "mlabonne/FineTome-100k" \
  --format-type auto \
  --training-type lora \
  --max-seq-length 2048 \
  --load-in-4bit \
  --output-dir ./outputs \
  --num-epochs 3 \
  --learning-rate 2e-4 \
  --batch-size 2 \
  --gradient-accumulation-steps 4 \
  --warmup-steps 5 \
  --weight-decay 0.01 \
  --random-seed 3407 \
  --lora-r 64 \
  --lora-alpha 16 \
  --lora-dropout 0.0 \
  --target-modules "q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj" \
  --gradient-checkpointing unsloth \
  --no-packing

# Or with a config file (CLI flags override config values)
unsloth train -c train_config.yaml

# Dry run - show resolved config without training
unsloth train -c train_config.yaml --dry-run
```

**All `unsloth train` flags:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--model` | TEXT | - | HF model ID or local path (required) |
| `--dataset` | TEXT | - | HuggingFace dataset ID |
| `--local-dataset` | TEXT | - | Path to local JSON/JSONL dataset |
| `--format-type` | TEXT | auto | Dataset format: auto, alpaca, chatml, sharegpt |
| `--training-type` | TEXT | lora | Training type: lora or full |
| `--max-seq-length` | INT | 2048 | Maximum sequence length |
| `--load-in-4bit / --no-load-in-4bit` | BOOL | True | Load model in 4-bit quantization |
| `--output-dir` | PATH | ./outputs | Directory for checkpoints |
| `--num-epochs` | INT | 3 | Number of training epochs |
| `--learning-rate` | FLOAT | 2e-4 | Learning rate |
| `--batch-size` | INT | 2 | Per-device batch size |
| `--gradient-accumulation-steps` | INT | 4 | Gradient accumulation steps |
| `--warmup-steps` | INT | 5 | Warmup steps |
| `--max-steps` | INT | 0 | Max steps (0 = use epochs) |
| `--save-steps` | INT | 0 | Save checkpoint every N steps |
| `--weight-decay` | FLOAT | 0.01 | Weight decay |
| `--random-seed` | INT | 3407 | Random seed |
| `--packing / --no-packing` | BOOL | False | Enable sequence packing |
| `--train-on-completions / --no-...` | BOOL | False | Train only on completions |
| `--gradient-checkpointing` | TEXT | unsloth | Options: unsloth, true, none |
| `--lora-r` | INT | 64 | LoRA rank |
| `--lora-alpha` | INT | 16 | LoRA alpha |
| `--lora-dropout` | FLOAT | 0.0 | LoRA dropout |
| `--target-modules` | TEXT | q,k,v,o,gate,up,down_proj | Comma-separated module names |
| `--vision-all-linear / --no-...` | BOOL | False | Apply LoRA to all linear (vision) |
| `--use-rslora / --no-use-rslora` | BOOL | False | Use Rank-Stabilized LoRA |
| `--use-loftq / --no-use-loftq` | BOOL | False | Use LoftQ initialization |
| `--finetune-vision-layers / --no-...` | BOOL | True | Fine-tune vision layers |
| `--finetune-language-layers / --no-...` | BOOL | True | Fine-tune language layers |
| `--finetune-attention-modules / --no-...` | BOOL | True | Fine-tune attention modules |
| `--finetune-mlp-modules / --no-...` | BOOL | True | Fine-tune MLP modules |
| `--enable-wandb / --no-enable-wandb` | BOOL | False | Enable W&B logging |
| `--wandb-project` | TEXT | unsloth-training | W&B project name |
| `--enable-tensorboard / --no-...` | BOOL | False | Enable TensorBoard |
| `--tensorboard-dir` | TEXT | runs | TensorBoard log directory |
| `--config / -c` | PATH | - | YAML/JSON config file |
| `--hf-token` | TEXT | env:HF_TOKEN | HuggingFace token |
| `--wandb-token` | TEXT | env:WANDB_API_KEY | W&B API key |
| `--dry-run` | - | - | Show config and exit |

### unsloth export

```bash
# Export to GGUF Q4_K_M
unsloth export ./outputs/checkpoint-100 ./exported --format gguf --quantization q4_k_m

# Export merged 16-bit
unsloth export ./outputs/checkpoint-100 ./exported --format merged-16bit

# Export LoRA adapter only
unsloth export ./outputs/checkpoint-100 ./exported --format lora

# Push to HuggingFace
unsloth export ./outputs/checkpoint-100 ./exported \
  --format gguf -q q5_k_m \
  --push-to-hub --repo-id username/model-name --hf-token $HF_TOKEN
```

Export formats: `merged-16bit`, `merged-4bit`, `gguf`, `lora`
GGUF quantizations: `q4_k_m`, `q5_k_m`, `q8_0`, `f16`

### unsloth inference

```bash
unsloth inference "unsloth/Qwen3.5-9B" "Explain quantum computing" \
  --temperature 0.7 --max-new-tokens 256 --system-prompt "You are a helpful assistant."
```

---

## 2. YAML Config File Format

The CLI accepts YAML or JSON config files via `--config / -c`. CLI flags override config values.

```yaml
# train_config.yaml
model: "unsloth/Qwen3.5-9B"

data:
  dataset: "mlabonne/FineTome-100k"        # HF dataset
  # local_dataset:                          # List of local file paths
  #   - "/path/to/train.jsonl"
  format_type: "auto"                       # auto | alpaca | chatml | sharegpt

training:
  training_type: "lora"                     # lora | full
  max_seq_length: 2048
  load_in_4bit: true
  output_dir: "./outputs"
  num_epochs: 3
  learning_rate: 0.0002
  batch_size: 2
  gradient_accumulation_steps: 4
  warmup_steps: 5
  max_steps: 0                              # 0 = use num_epochs
  save_steps: 0                             # 0 = save at end only
  weight_decay: 0.01
  random_seed: 3407
  packing: false
  train_on_completions: false
  gradient_checkpointing: "unsloth"         # unsloth | true | none

lora:
  lora_r: 64
  lora_alpha: 16
  lora_dropout: 0.0
  target_modules: "q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj"
  vision_all_linear: false
  use_rslora: false
  use_loftq: false
  finetune_vision_layers: true
  finetune_language_layers: true
  finetune_attention_modules: true
  finetune_mlp_modules: true

logging:
  enable_wandb: false
  wandb_project: "unsloth-training"
  enable_tensorboard: false
  tensorboard_dir: "runs"
```

---

## 3. Python API (Direct Script, No UI)

The Unsloth Python API uses `FastLanguageModel` for loading and LoRA config, plus HuggingFace's `SFTTrainer`. This runs completely headless.

### Minimal QLoRA Fine-Tune Script for Qwen 3.5 9B on RTX 3090

```python
#!/usr/bin/env python3
"""
Headless Unsloth QLoRA fine-tuning script.
Run inside distrobox "ai" with the unsloth venv activated:
  distrobox enter ai
  source ~/ai-drive/ai-suite/unsloth-studio/bin/activate
  python train_qwen.py
"""

from unsloth import FastLanguageModel
from unsloth.chat_templates import get_chat_template
from trl import SFTTrainer
from transformers import TrainingArguments
from datasets import load_dataset

# ── 1. Load model in 4-bit ──────────────────────────────────────
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Qwen3.5-9B",      # HF model ID
    max_seq_length=2048,
    dtype=None,                             # Auto-detect (bf16 on Ampere+)
    load_in_4bit=True,                      # QLoRA 4-bit quantization
    token=None,                             # Set if gated model
)

# ── 2. Configure LoRA adapters ──────────────────────────────────
model = FastLanguageModel.get_peft_model(
    model,
    r=64,                                   # LoRA rank
    lora_alpha=16,                          # LoRA alpha
    lora_dropout=0.0,                       # No dropout (Unsloth optimized)
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    use_gradient_checkpointing="unsloth",   # 70% less VRAM
    use_rslora=False,
    random_state=3407,
    max_seq_length=2048,
)

# ── 3. Apply chat template ─────────────────────────────────────
tokenizer = get_chat_template(tokenizer, chat_template="chatml")

# ── 4. Load dataset ────────────────────────────────────────────
# Option A: HuggingFace dataset
dataset = load_dataset("mlabonne/FineTome-100k", split="train")

# Option B: Local JSON/JSONL
# from datasets import load_dataset
# dataset = load_dataset("json", data_files="train_data.jsonl", split="train")

# Format function for chat-style data
def format_prompts(examples):
    texts = []
    for convo in examples["conversations"]:
        text = tokenizer.apply_chat_template(convo, tokenize=False, add_generation_prompt=False)
        texts.append(text)
    return {"text": texts}

dataset = dataset.map(format_prompts, batched=True)

# ── 5. Configure trainer ───────────────────────────────────────
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    args=TrainingArguments(
        output_dir="./outputs",
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        num_train_epochs=3,
        learning_rate=2e-4,
        warmup_steps=5,
        weight_decay=0.01,
        fp16=not False,                    # Use fp16 on non-bf16 GPUs
        bf16=False,                        # RTX 3090 supports bf16 too
        logging_steps=1,
        save_steps=100,
        seed=3407,
        optim="adamw_8bit",
        lr_scheduler_type="linear",
    ),
    dataset_text_field="text",
    max_seq_length=2048,
    packing=False,
)

# ── 6. Train ───────────────────────────────────────────────────
trainer.train()

# ── 7. Save LoRA adapter ──────────────────────────────────────
model.save_pretrained("./outputs/lora_adapter")
tokenizer.save_pretrained("./outputs/lora_adapter")

# ── 8. Export to GGUF ──────────────────────────────────────────
model.save_pretrained_gguf(
    "./outputs/gguf",
    tokenizer,
    quantization_method="q4_k_m",          # q4_k_m, q5_k_m, q8_0, f16
)

# Optional: push to HuggingFace Hub
# model.push_to_hub_gguf("username/model-name", tokenizer, quantization_method="q4_k_m")

print("Training complete!")
```

### Key Python API Functions

```python
# FastLanguageModel.from_pretrained() parameters:
#   model_name, max_seq_length, dtype, load_in_4bit, load_in_8bit,
#   load_in_16bit, full_finetuning, token, device_map, rope_scaling,
#   trust_remote_code, use_gradient_checkpointing, fast_inference,
#   gpu_memory_utilization, max_lora_rank

# FastLanguageModel.get_peft_model() parameters:
#   model, r=16, target_modules=[...], lora_alpha=16, lora_dropout=0.0,
#   bias="none", layers_to_transform=None, use_gradient_checkpointing="unsloth",
#   random_state=3407, max_seq_length=2048, use_rslora=False,
#   modules_to_save=None, init_lora_weights=True, loftq_config={}

# Save/Export methods on the model:
#   model.save_pretrained("path")                    # Save LoRA adapter
#   model.save_pretrained_merged("path", tokenizer)  # Save merged model
#   model.save_pretrained_gguf("path", tokenizer, quantization_method="q4_k_m")
#   model.push_to_hub("repo_id", token="...")
#   model.push_to_hub_gguf("repo_id", tokenizer, quantization_method="q4_k_m")
```

---

## 4. Unsloth Studio REST API

Studio runs a FastAPI server with full REST API. All routes are under `/api/` and require JWT authentication.

### Authentication

```bash
# Login to get JWT token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "YOUR_PASSWORD"}'

# Response: {"access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer"}

# Use token in subsequent requests:
# Authorization: Bearer eyJ...
```

### Training API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/train/start` | Start a training job |
| POST | `/api/train/stop` | Stop current training (optional save) |
| POST | `/api/train/reset` | Reset training state |
| GET | `/api/train/status` | Get training status/phase |
| GET | `/api/train/metrics` | Get loss/lr/step histories |
| GET | `/api/train/progress` | SSE stream of real-time progress |
| GET | `/api/train/hardware` | GPU utilization snapshot |

### Start Training via API

```bash
TOKEN="eyJ..."

curl -X POST http://localhost:8000/api/train/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "unsloth/Qwen3.5-9B",
    "training_type": "lora",
    "load_in_4bit": true,
    "max_seq_length": 2048,
    "hf_dataset": "mlabonne/FineTome-100k",
    "format_type": "auto",
    "num_epochs": 3,
    "learning_rate": 2e-4,
    "batch_size": 2,
    "gradient_accumulation_steps": 4,
    "warmup_steps": 5,
    "weight_decay": 0.01,
    "random_seed": 3407,
    "packing": false,
    "use_lora": true,
    "lora_r": 64,
    "lora_alpha": 16,
    "lora_dropout": 0.0,
    "target_modules": ["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
    "gradient_checkpointing": "unsloth",
    "use_rslora": false,
    "train_on_completions": false,
    "enable_wandb": false,
    "enable_tensorboard": false
  }'
```

### Monitor Training via API

```bash
# Poll status
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/train/status

# Get metrics history
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/train/metrics

# SSE stream (real-time)
curl -N -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/train/progress

# Stop training (save checkpoint)
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"save": true}' \
  http://localhost:8000/api/train/stop
```

### Other API Routes

| Prefix | Purpose |
|--------|---------|
| `/api/auth/*` | Login, refresh token, change password |
| `/api/models/*` | Browse/search HF models |
| `/api/datasets/*` | Browse/manage datasets |
| `/api/data-recipe/*` | Dataset creation/transformation (MCP, jobs) |
| `/api/export/*` | Export checkpoints to GGUF/merged/LoRA |
| `/api/inference/*` | Run inference on loaded models |
| `/v1/*` | OpenAI-compatible API (chat completions) |
| `/api/health` | Health check |

---

## 5. Batch/Headless Training

**Yes, fully supported.** Three approaches, from simplest to most flexible:

### Approach A: CLI with Config File (Recommended for BoltHands)

```bash
#!/bin/bash
# train-bolthands.sh - headless training script
distrobox enter ai -- bash -c "
  source ~/ai-drive/ai-suite/unsloth-studio/bin/activate
  unsloth train -c ~/bolthands/configs/train.yaml
"
```

The CLI uses `studio.backend.core.training.trainer.UnslothTrainer` internally and blocks until training completes. Supports Ctrl+C for graceful stop.

### Approach B: Python Script (Most Flexible)

```bash
distrobox enter ai -- bash -c "
  source ~/ai-drive/ai-suite/unsloth-studio/bin/activate
  python ~/bolthands/scripts/train_qwen.py
"
```

See the full Python script in section 3 above.

### Approach C: Studio REST API (For Background Jobs)

Start Studio in the background, then trigger training via API:

```bash
# Start studio (background)
distrobox enter ai -- bash -c "
  source ~/ai-drive/ai-suite/unsloth-studio/bin/activate
  unsloth studio -p 8000 -q &
"

# Trigger training from BoltHands via HTTP
curl -X POST http://localhost:8000/api/train/start -H "Authorization: Bearer $TOKEN" ...

# Monitor via SSE
curl -N http://localhost:8000/api/train/progress -H "Authorization: Bearer $TOKEN"
```

### End-to-End Automated Pipeline Example

```bash
#!/bin/bash
# Full pipeline: train -> export to GGUF -> deploy
set -e

VENV="source ~/ai-drive/ai-suite/unsloth-studio/bin/activate"
CONFIG="~/bolthands/configs/train.yaml"
OUTPUT="~/ai-drive/ai-suite/unsloth-studio/outputs"
EXPORT_DIR="~/ai-drive/ai-suite/models"

distrobox enter ai -- bash -c "
  $VENV

  # Train
  unsloth train -c $CONFIG

  # Find latest checkpoint
  LATEST=\$(ls -td $OUTPUT/*/checkpoint-* 2>/dev/null | head -1)

  if [ -n \"\$LATEST\" ]; then
    # Export to GGUF
    unsloth export \"\$LATEST\" $EXPORT_DIR/bolthands-latest \
      --format gguf --quantization q4_k_m

    echo 'Training and export complete!'
  else
    echo 'No checkpoint found!'
    exit 1
  fi
"
```

---

## 6. Venv / Environment Details

### Two Separate Venvs

Unsloth Studio creates **two separate venvs**:

1. **Outer venv** (where `unsloth` CLI lives):
   - `~/ai-drive/ai-suite/unsloth-studio/` (user-created during install)
   - Contains: `unsloth`, `unsloth_cli`, `unsloth_zoo`, transformers, torch, etc.
   - The `unsloth` command itself lives here
   - **This is the venv for CLI training and Python scripts**

2. **Inner Studio venv** (created by `unsloth studio setup`):
   - `~/.unsloth/studio/.venv/`
   - Contains: `studio` package (FastAPI backend, frontend, training worker)
   - Also has its own copy of torch, transformers, unsloth, etc.
   - Used exclusively by `unsloth studio` server process
   - Also contains `~/.unsloth/studio/.venv_t5/` (separate T5 venv)

### Which Venv to Use

- **For `unsloth train` CLI:** Use the outer venv (`~/ai-drive/ai-suite/unsloth-studio/`)
- **For Python scripts:** Use the outer venv (it has `FastLanguageModel` etc.)
- **For Studio REST API:** Studio manages its own inner venv automatically
- **Important:** The `unsloth train` command internally imports from `studio.backend.core.training.trainer` which is in the inner venv. The CLI handles this bridging automatically.

### Running Training Scripts

```bash
# Method 1: Activate outer venv + run CLI
distrobox enter ai -- bash -c "
  source ~/ai-drive/ai-suite/unsloth-studio/bin/activate
  unsloth train --model 'unsloth/Qwen3.5-9B' --dataset 'mlabonne/FineTome-100k'
"

# Method 2: Activate outer venv + run Python script directly
distrobox enter ai -- bash -c "
  source ~/ai-drive/ai-suite/unsloth-studio/bin/activate
  python my_training_script.py
"

# Method 3: Use inner venv Python for scripts that need studio internals
distrobox enter ai -- bash -c "
  ~/.unsloth/studio/.venv/bin/python my_script.py
"
```

---

## 7. BoltHands Integration Recommendations

For a self-improving training loop, the recommended approach is:

1. **Use `unsloth train -c config.yaml`** for the training step -- simplest, most robust, fully headless
2. **Use `unsloth export`** to convert checkpoints to GGUF after training
3. **Generate YAML configs programmatically** from BoltHands before each training run
4. **Parse exit codes** -- `unsloth train` returns 0 on success, 1 on training error, 2 on config error
5. **For real-time monitoring**, either:
   - Parse stdout/stderr from the CLI process
   - Or run Studio and use the SSE `/api/train/progress` endpoint
6. **All training runs output to `./outputs/`** (or `--output-dir`), containing timestamped checkpoint directories

### Dataset Format for Local Files

BoltHands can generate training data as JSONL in these formats:

```jsonl
# ShareGPT format (recommended)
{"conversations": [{"from": "human", "value": "..."}, {"from": "gpt", "value": "..."}]}

# Alpaca format
{"instruction": "...", "input": "...", "output": "..."}

# ChatML format
{"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
```

Use `--local-dataset /path/to/data.jsonl --format-type sharegpt` (or `auto` for auto-detection).
