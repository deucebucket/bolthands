#!/usr/bin/env python3
"""Quick speed test for training with optimized settings."""

import time

from unsloth import FastLanguageModel
from datasets import load_dataset
from trl import SFTTrainer, SFTConfig

print("Loading 4B model...")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Qwen3.5-4B",
    max_seq_length=1024,
    dtype=None,
    load_in_4bit=True,
)

print("Applying LoRA (dropout=0 for fast patching)...")
model = FastLanguageModel.get_peft_model(
    model, r=32, lora_alpha=64,
    lora_dropout=0,  # KEY: enables Unsloth fast kernel patching
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                     "gate_proj", "up_proj", "down_proj"],
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
    max_seq_length=1024,
    use_rslora=True,
)

print("Loading dataset...")
ds = load_dataset(
    "json",
    data_files="/home/deucebucket/ai-drive/bolthands/training-data/final/train.jsonl",
    split="train",
)
print(f"  {len(ds)} examples")

print("Starting 20-step speed test...")
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=ds,
    args=SFTConfig(
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,
        max_steps=20,
        learning_rate=2e-4,
        warmup_steps=2,
        bf16=True,
        optim="adamw_8bit",
        max_seq_length=1024,
        dataset_text_field="text",
        logging_steps=5,
        output_dir="/tmp/speed-test",
        seed=42,
    ),
)

start = time.time()
trainer.train()
elapsed = time.time() - start

print(f"\n{'='*40}")
print(f"SPEED TEST RESULTS")
print(f"{'='*40}")
print(f"20 steps in {elapsed:.1f}s = {elapsed/20:.1f}s per step")
print(f"Estimated 4384 steps (2 epochs): {4384 * elapsed / 20 / 3600:.1f} hours")
print(f"Estimated 2192 steps (1 epoch):  {2192 * elapsed / 20 / 3600:.1f} hours")
print(f"{'='*40}")
