#!/usr/bin/env python3
"""
Direct Unsloth QLoRA training script for BoltHands 9B.

Usage (inside distrobox "ai"):
  source ~/ai-drive/ai-suite/unsloth-studio/bin/activate
  export HF_TOKEN=your_token_here
  python training/train_direct.py --dataset ~/ai-drive/bolthands/training-data/final/train.jsonl
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Train BoltHands 9B")
    parser.add_argument("--dataset", required=True, help="Path to training JSONL")
    parser.add_argument("--output-dir", default=os.path.expanduser("~/ai-drive/bolthands/checkpoints"))
    parser.add_argument("--model", default="unsloth/Qwen3.5-9B")
    parser.add_argument("--max-seq-length", type=int, default=4096)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--grad-accum", type=int, default=8)
    parser.add_argument("--lora-r", type=int, default=64)
    parser.add_argument("--lora-alpha", type=int, default=128)
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = Path(args.output_dir) / f"bolthands-{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== BoltHands 9B Training ===")
    print(f"Model: {args.model}")
    print(f"Dataset: {args.dataset}")
    print(f"Output: {output_dir}")
    print(f"LoRA: r={args.lora_r}, alpha={args.lora_alpha}")
    print(f"Epochs: {args.epochs}, LR: {args.lr}")
    print(f"Batch: {args.batch_size} x {args.grad_accum} = {args.batch_size * args.grad_accum}")
    print()

    # Step 1: Load model
    print("Loading model...")
    from unsloth import FastLanguageModel
    import torch

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.model,
        max_seq_length=args.max_seq_length,
        dtype=None,
        load_in_4bit=True,
    )

    # Step 2: Apply LoRA
    print("Applying LoRA...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0,  # Must be 0 for Unsloth fast kernel patching
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
        max_seq_length=args.max_seq_length,
        use_rslora=True,
    )

    # Step 3: Load dataset
    print("Loading dataset...")
    from datasets import load_dataset

    dataset = load_dataset("json", data_files=args.dataset, split="train")
    print(f"  {len(dataset)} training examples loaded")

    # Step 4: Train
    print("Starting training...")
    from trl import SFTTrainer, SFTConfig

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=SFTConfig(
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=args.grad_accum,
            num_train_epochs=args.epochs,
            learning_rate=args.lr,
            lr_scheduler_type="cosine",
            warmup_ratio=0.05,
            fp16=not torch.cuda.is_bf16_supported(),
            bf16=torch.cuda.is_bf16_supported(),
            optim="adamw_8bit",
            max_seq_length=args.max_seq_length,
            dataset_text_field="text",
            logging_steps=10,
            save_strategy="steps",
            save_steps=500,
            save_total_limit=3,
            output_dir=str(output_dir),
            seed=42,
            weight_decay=0.01,
        ),
    )

    stats = trainer.train()
    print(f"\nTraining complete!")
    print(f"Stats: {stats}")

    # Step 5: Save LoRA adapter
    lora_dir = output_dir / "lora-adapter"
    print(f"Saving LoRA adapter to {lora_dir}...")
    model.save_pretrained(str(lora_dir))
    tokenizer.save_pretrained(str(lora_dir))

    # Step 6: Export to GGUF
    for quant in ["q4_k_m", "q5_k_m"]:
        gguf_dir = output_dir / f"gguf-{quant}"
        print(f"Exporting GGUF ({quant}) to {gguf_dir}...")
        try:
            model.save_pretrained_gguf(
                str(gguf_dir),
                tokenizer,
                quantization_method=quant,
            )
        except Exception as e:
            print(f"  GGUF export ({quant}) failed: {e}")
            print(f"  You can export manually later with: unsloth export {lora_dir} {gguf_dir} --format gguf -q {quant}")

    # Copy to models dir
    models_dir = Path.home() / "ai-drive" / "ai-suite" / "models"
    for quant in ["q4_k_m", "q5_k_m"]:
        gguf_dir = output_dir / f"gguf-{quant}"
        gguf_files = list(gguf_dir.glob("*.gguf")) if gguf_dir.exists() else []
        for gguf_file in gguf_files:
            dest = models_dir / f"bolthands-9b-{quant}.gguf"
            print(f"Copying {gguf_file.name} → {dest}")
            import shutil
            shutil.copy2(str(gguf_file), str(dest))

    print(f"\n=== Done! ===")
    print(f"LoRA adapter: {lora_dir}")
    print(f"Checkpoints: {output_dir}")


if __name__ == "__main__":
    main()
