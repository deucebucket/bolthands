"""Tests for the dataset mixer."""

import json
from pathlib import Path

from data.mixer import DatasetMixer, MixerConfig


class TestMixerConfig:
    def test_validates_ratios(self):
        config = MixerConfig(ratios={"a": 0.6, "b": 0.6})  # sums to 1.2
        config.validate()
        total = sum(config.ratios.values())
        assert abs(total - 1.0) < 0.01

    def test_valid_ratios_unchanged(self):
        config = MixerConfig(ratios={"a": 0.5, "b": 0.5})
        config.validate()
        assert config.ratios["a"] == 0.5


class TestDatasetMixer:
    def test_mix_basic(self, tmp_path):
        # Create two source files
        source_a = tmp_path / "domain_a.jsonl"
        source_b = tmp_path / "domain_b.jsonl"

        with open(source_a, "w") as f:
            for i in range(100):
                f.write(json.dumps({"text": f"example a {i}", "domain": "a"}) + "\n")

        with open(source_b, "w") as f:
            for i in range(100):
                f.write(json.dumps({"text": f"example b {i}", "domain": "b"}) + "\n")

        config = MixerConfig(
            ratios={"domain_a": 0.6, "domain_b": 0.4},
            total_target=50,
            eval_split=0.1,
            output_dir=tmp_path / "output",
        )
        mixer = DatasetMixer(config)
        train_path, eval_path = mixer.mix({"domain_a": source_a, "domain_b": source_b})

        assert train_path.exists()
        assert eval_path.exists()

        with open(train_path) as f:
            train_lines = f.readlines()
        with open(eval_path) as f:
            eval_lines = f.readlines()

        total = len(train_lines) + len(eval_lines)
        assert total == 50  # total_target

    def test_mix_handles_missing_files(self, tmp_path):
        config = MixerConfig(
            ratios={"missing": 1.0},
            total_target=10,
            output_dir=tmp_path / "output",
        )
        mixer = DatasetMixer(config)
        train_path, eval_path = mixer.mix({"missing": tmp_path / "nonexistent.jsonl"})

        # Should produce empty files, not crash
        assert train_path.exists()

    def test_oversampling(self, tmp_path):
        """When source has fewer examples than target, should oversample."""
        source = tmp_path / "small.jsonl"
        with open(source, "w") as f:
            for i in range(5):
                f.write(json.dumps({"text": f"example {i}"}) + "\n")

        config = MixerConfig(
            ratios={"small": 1.0},
            total_target=20,
            eval_split=0.0,
            output_dir=tmp_path / "output",
        )
        mixer = DatasetMixer(config)
        train_path, _ = mixer.mix({"small": source})

        with open(train_path) as f:
            lines = f.readlines()
        assert len(lines) == 20  # oversampled from 5 to 20

    def test_eval_split(self, tmp_path):
        source = tmp_path / "data.jsonl"
        with open(source, "w") as f:
            for i in range(100):
                f.write(json.dumps({"text": f"example {i}"}) + "\n")

        config = MixerConfig(
            ratios={"data": 1.0},
            total_target=100,
            eval_split=0.2,
            output_dir=tmp_path / "output",
        )
        mixer = DatasetMixer(config)
        train_path, eval_path = mixer.mix({"data": source})

        with open(train_path) as f:
            train_count = len(f.readlines())
        with open(eval_path) as f:
            eval_count = len(f.readlines())

        assert eval_count == 20  # 20% of 100
        assert train_count == 80

    def test_report_distribution(self, tmp_path):
        source = tmp_path / "data.jsonl"
        with open(source, "w") as f:
            for i in range(50):
                f.write(json.dumps({"text": f"ex {i}"}) + "\n")

        config = MixerConfig(
            ratios={"data": 0.7, "other": 0.3},
            total_target=100,
        )
        mixer = DatasetMixer(config)
        report = mixer.report_distribution({"data": source})
        assert "data" in report
        assert "other" in report
