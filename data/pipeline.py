"""
End-to-end BoltHands training data pipeline.

Orchestrates: download HF datasets → convert → generate synthetic → validate → mix

Usage:
    python -m data.pipeline --output-dir ~/ai-drive/bolthands/training-data
    python -m data.pipeline --step convert  # run only conversion step
    python -m data.pipeline --step generate --llm-url http://localhost:8080  # generate synthetic data
    python -m data.pipeline --step validate
    python -m data.pipeline --step mix
"""

import json
import logging
from pathlib import Path

import click

from .mixer import DatasetMixer, MixerConfig, DEFAULT_RATIOS
from .validator import Validator

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = Path.home() / "ai-drive" / "bolthands" / "training-data"

# Domain → generator class mapping
GENERATOR_REGISTRY: dict[str, str] = {
    "systemd": "data.generators.systemd:SystemdGenerator",
    "flipper": "data.generators.flipper:FlipperGenerator",
    "windows": "data.generators.windows:WindowsGenerator",
    "plex": "data.generators.plex:PlexGenerator",
    "arr": "data.generators.arr:ArrGenerator",
    "openclaw": "data.generators.openclaw:OpenClawGenerator",
    "comfyui": "data.generators.comfyui:ComfyUIGenerator",
    "tts": "data.generators.tts:TTSGenerator",
    "rvc": "data.generators.rvc:RVCGenerator",
    "music": "data.generators.music:MusicGenerator",
    "llm": "data.generators.llm_mgmt:LLMGenerator",
    "dashboard": "data.generators.dashboard:DashboardGenerator",
    "mantella": "data.generators.mantella:MantellaGenerator",
    "steam": "data.generators.steam:SteamGenerator",
    "tailscale": "data.generators.tailscale:TailscaleGenerator",
    "cross_domain": "data.generators.cross_domain:CrossDomainGenerator",
}

# HF dataset → converter class mapping
CONVERTER_REGISTRY: dict[str, dict] = {
    "hf_hermes": {
        "class": "data.converters.hermes:HermesConverter",
        "dataset": "NousResearch/hermes-function-calling-v1",
        "max_examples": None,  # use all
    },
    "hf_xlam": {
        "class": "data.converters.xlam:XlamConverter",
        "dataset": "Salesforce/xlam-function-calling-60k",
        "max_examples": 20000,
    },
    "hf_glaive": {
        "class": "data.converters.glaive:GlaiveConverter",
        "dataset": "glaiveai/glaive-function-calling-v2",
        "max_examples": 10000,
    },
    "hf_nemotron": {
        "class": "data.converters.nemotron:NemotronConverter",
        "dataset": "nvidia/Nemotron-RL-Agentic-Function-Calling-Pivot-v1",
        "max_examples": 5000,
    },
}

# How many synthetic examples to generate per domain
SYNTHETIC_TARGETS = {
    "systemd": 10000,
    "flipper": 8000,
    "windows": 15000,
    "plex": 12000,
    "arr": 23000,  # covers sonarr + radarr + lidarr + prowlarr
    "openclaw": 12000,
    "comfyui": 8000,
    "tts": 6000,
    "rvc": 4000,
    "music": 3000,
    "llm": 5000,
    "dashboard": 5000,
    "mantella": 3000,
    "steam": 3000,
    "tailscale": 2000,
    "cross_domain": 8000,
}


def _import_class(dotted_path: str):
    """Import a class from a dotted module:ClassName path."""
    module_path, class_name = dotted_path.rsplit(":", 1)
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def step_convert(output_dir: Path):
    """Download and convert HuggingFace datasets."""
    converted_dir = output_dir / "converted"
    converted_dir.mkdir(parents=True, exist_ok=True)

    for name, config in CONVERTER_REGISTRY.items():
        output_file = converted_dir / f"{name}.jsonl"
        if output_file.exists():
            logger.info(f"Skipping {name} — already converted at {output_file}")
            continue

        logger.info(f"Converting {name} from {config['dataset']}...")
        converter_cls = _import_class(config["class"])
        converter = converter_cls()
        converter.convert_dataset(
            config["dataset"],
            output_file,
            max_examples=config.get("max_examples"),
        )
        logger.info(f"  → {output_file}")


def step_generate(output_dir: Path, llm_url: str | None = None):
    """Generate synthetic training data for all domains."""
    synthetic_dir = output_dir / "synthetic"
    synthetic_dir.mkdir(parents=True, exist_ok=True)

    for domain, target in SYNTHETIC_TARGETS.items():
        output_file = synthetic_dir / f"{domain}.jsonl"
        if output_file.exists():
            existing = sum(1 for _ in open(output_file))
            if existing >= target:
                logger.info(f"Skipping {domain} — already has {existing} examples")
                continue
            logger.info(f"{domain} has {existing}/{target} — generating {target - existing} more")
            target = target - existing

        if domain not in GENERATOR_REGISTRY:
            logger.warning(f"No generator registered for {domain}")
            continue

        logger.info(f"Generating {target} examples for {domain}...")
        generator_cls = _import_class(GENERATOR_REGISTRY[domain])
        generator = generator_cls(llm_url=llm_url)
        generator.generate_to_jsonl(target, output_file)
        logger.info(f"  → {output_file}")


def step_validate(output_dir: Path):
    """Validate all generated and converted data."""
    validator = Validator()
    validated_dir = output_dir / "validated"
    validated_dir.mkdir(parents=True, exist_ok=True)

    for source_dir in [output_dir / "converted", output_dir / "synthetic"]:
        if not source_dir.exists():
            continue
        for jsonl_file in sorted(source_dir.glob("*.jsonl")):
            output_file = validated_dir / jsonl_file.name
            logger.info(f"Validating {jsonl_file.name}...")
            report = validator.validate_file(jsonl_file, output_file)
            logger.info(f"  {report.summary()}")
            validator.reset()


def step_mix(output_dir: Path, total_target: int = 165000, eval_split: float = 0.05):
    """Mix validated data into final training dataset."""
    validated_dir = output_dir / "validated"
    final_dir = output_dir / "final"

    # Build source file mapping
    source_files = {}
    for jsonl_file in validated_dir.glob("*.jsonl"):
        domain = jsonl_file.stem
        source_files[domain] = jsonl_file

    config = MixerConfig(
        ratios=DEFAULT_RATIOS,
        total_target=total_target,
        eval_split=eval_split,
        output_dir=final_dir,
    )
    mixer = DatasetMixer(config)

    # Report planned distribution
    logger.info(mixer.report_distribution(source_files))

    # Mix
    train_path, eval_path = mixer.mix(source_files)
    logger.info(f"Final dataset: {train_path} + {eval_path}")


@click.command()
@click.option("--output-dir", type=click.Path(), default=str(DEFAULT_OUTPUT_DIR), help="Output directory")
@click.option("--step", type=click.Choice(["all", "convert", "generate", "validate", "mix"]), default="all")
@click.option("--llm-url", type=str, default=None, help="LLM endpoint for synthetic generation")
@click.option("--total-target", type=int, default=165000, help="Total training examples target")
@click.option("--eval-split", type=float, default=0.05, help="Fraction held out for eval")
def main(output_dir: str, step: str, llm_url: str | None, total_target: int, eval_split: float):
    """BoltHands training data pipeline."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if step in ("all", "convert"):
        step_convert(out)

    if step in ("all", "generate"):
        step_generate(out, llm_url)

    if step in ("all", "validate"):
        step_validate(out)

    if step in ("all", "mix"):
        step_mix(out, total_target, eval_split)


if __name__ == "__main__":
    main()
