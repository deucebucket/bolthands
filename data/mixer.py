"""
Dataset mixer for BoltHands training data.

Combines multiple domain-specific JSONL files into a single training dataset
with configurable ratios, shuffling, and train/eval splitting.
"""

import json
import logging
import random
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Default domain ratios — how much of the final dataset each domain should be
DEFAULT_RATIOS = {
    # HF converted datasets (base function calling)
    "hf_hermes": 0.07,
    "hf_xlam": 0.08,
    "hf_glaive": 0.05,
    "hf_nemotron": 0.03,
    # Synthetic per-domain
    "windows": 0.10,
    "plex": 0.07,
    "sonarr": 0.05,
    "radarr": 0.04,
    "lidarr": 0.03,
    "prowlarr": 0.02,
    "openclaw": 0.07,
    "systemd": 0.06,
    "flipper": 0.05,
    "comfyui": 0.05,
    "tts": 0.04,
    "rvc": 0.03,
    "music": 0.02,
    "llm": 0.03,
    "dashboard": 0.03,
    "mantella": 0.02,
    "steam": 0.02,
    "tailscale": 0.01,
    # Cross-domain
    "cross_domain": 0.05,
    # Anti-forgetting (general conversation)
    "general": 0.05,
}


@dataclass
class MixerConfig:
    """Configuration for dataset mixing."""

    ratios: dict[str, float]
    total_target: int = 165000
    eval_split: float = 0.05
    seed: int = 42
    output_dir: Path = Path("output")

    def validate(self):
        total = sum(self.ratios.values())
        if abs(total - 1.0) > 0.01:
            logger.warning(f"Ratios sum to {total:.3f}, not 1.0 — will normalize")
            factor = 1.0 / total
            self.ratios = {k: v * factor for k, v in self.ratios.items()}


class DatasetMixer:
    """Mixes multiple JSONL files into a balanced training dataset."""

    def __init__(self, config: MixerConfig | None = None):
        self.config = config or MixerConfig(ratios=DEFAULT_RATIOS)
        self.config.validate()

    def mix(self, source_files: dict[str, Path]) -> tuple[Path, Path]:
        """Mix source files according to ratios.

        Args:
            source_files: dict mapping domain name to JSONL file path

        Returns:
            tuple of (train_path, eval_path)
        """
        random.seed(self.config.seed)
        all_examples = []

        for domain, file_path in source_files.items():
            if not file_path.exists():
                logger.warning(f"Source file not found for {domain}: {file_path}")
                continue

            ratio = self.config.ratios.get(domain, 0)
            target_count = int(self.config.total_target * ratio)

            if target_count == 0:
                logger.info(f"Skipping {domain} (ratio=0)")
                continue

            examples = self._load_jsonl(file_path)

            if len(examples) == 0:
                logger.warning(f"Empty source file for {domain}: {file_path}")
                continue

            # Sample or oversample to reach target
            if len(examples) >= target_count:
                sampled = random.sample(examples, target_count)
            else:
                # Oversample with repetition
                repeats = (target_count // len(examples)) + 1
                pool = examples * repeats
                sampled = random.sample(pool, target_count)
                logger.info(
                    f"{domain}: oversampled {len(examples)} → {target_count} "
                    f"({repeats}x repetition)"
                )

            all_examples.extend(sampled)
            logger.info(f"{domain}: {len(sampled)} examples (target: {target_count})")

        # Shuffle
        random.shuffle(all_examples)
        logger.info(f"Total mixed examples: {len(all_examples)}")

        # Split train/eval
        eval_count = int(len(all_examples) * self.config.eval_split)
        eval_examples = all_examples[:eval_count]
        train_examples = all_examples[eval_count:]

        # Write output
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        train_path = self.config.output_dir / "train.jsonl"
        eval_path = self.config.output_dir / "eval.jsonl"

        self._write_jsonl(train_path, train_examples)
        self._write_jsonl(eval_path, eval_examples)

        logger.info(f"Train: {len(train_examples)} examples → {train_path}")
        logger.info(f"Eval: {len(eval_examples)} examples → {eval_path}")

        return train_path, eval_path

    def _load_jsonl(self, path: Path) -> list[dict]:
        examples = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        examples.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return examples

    def _write_jsonl(self, path: Path, examples: list[dict]):
        with open(path, "w") as f:
            for ex in examples:
                f.write(json.dumps(ex) + "\n")

    def report_distribution(self, source_files: dict[str, Path]) -> str:
        """Report the expected distribution of the mixed dataset."""
        lines = ["Domain Distribution Plan:", ""]
        total = 0
        for domain, ratio in sorted(self.config.ratios.items(), key=lambda x: -x[1]):
            target = int(self.config.total_target * ratio)
            available = 0
            if domain in source_files and source_files[domain].exists():
                available = sum(1 for _ in open(source_files[domain]))
            status = "OK" if available >= target else f"NEED {target - available} more"
            lines.append(f"  {domain:20s} {ratio:5.1%}  target={target:6d}  available={available:6d}  {status}")
            total += target
        lines.append(f"\n  {'TOTAL':20s}        target={total:6d}")
        return "\n".join(lines)
