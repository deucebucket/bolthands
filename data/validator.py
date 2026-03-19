"""
Validates BoltHands training data for:
1. JSON syntax in tool calls and responses
2. Tool name exists in schemas
3. Required arguments present
4. Conversation structure (proper role ordering)
5. Deduplication (fuzzy matching on user prompts)
"""

import json
import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMAS_DIR = Path(__file__).parent / "schemas"

TOOL_CALL_PATTERN = re.compile(r"<tool_call>\s*({.*?})\s*</tool_call>", re.DOTALL)
TOOL_RESPONSE_PATTERN = re.compile(r"<tool_response>\s*({.*?})\s*</tool_response>", re.DOTALL)


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    total: int = 0
    valid: int = 0
    invalid: int = 0
    duplicates_removed: int = 0
    errors_by_type: dict[str, int] = field(default_factory=dict)

    def summary(self) -> str:
        lines = [
            f"Total examples: {self.total}",
            f"Valid: {self.valid} ({self.valid / max(self.total, 1) * 100:.1f}%)",
            f"Invalid: {self.invalid} ({self.invalid / max(self.total, 1) * 100:.1f}%)",
            f"Duplicates removed: {self.duplicates_removed}",
        ]
        if self.errors_by_type:
            lines.append("Errors by type:")
            for err_type, count in sorted(self.errors_by_type.items(), key=lambda x: -x[1]):
                lines.append(f"  {err_type}: {count}")
        return "\n".join(lines)


class Validator:
    """Validates training examples against tool schemas."""

    def __init__(self):
        self.tool_schemas = self._load_all_schemas()
        self.tool_names = set(self.tool_schemas.keys())
        self._seen_hashes: set[str] = set()

    def _load_all_schemas(self) -> dict[str, dict]:
        """Load all tool schemas and index by tool name."""
        schemas = {}
        if not SCHEMAS_DIR.exists():
            logger.warning(f"Schemas directory not found: {SCHEMAS_DIR}")
            return schemas

        for schema_file in SCHEMAS_DIR.glob("*.json"):
            try:
                with open(schema_file) as f:
                    tools = json.load(f)
                for tool in tools:
                    name = tool["function"]["name"]
                    schemas[name] = tool["function"]
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load schema {schema_file}: {e}")
        return schemas

    def validate_example(self, example: dict) -> ValidationResult:
        """Validate a single training example."""
        errors = []
        warnings = []

        text = example.get("text", "")
        if not text:
            return ValidationResult(valid=False, errors=["Empty text field"])

        # Check basic ChatML structure
        if "<|im_start|>" not in text:
            errors.append("missing_chatml_tags")

        if "<|im_start|>system" not in text:
            warnings.append("missing_system_message")

        if "<|im_start|>user" not in text:
            errors.append("missing_user_message")

        if "<|im_start|>assistant" not in text:
            errors.append("missing_assistant_message")

        # Validate tool calls
        tool_calls = TOOL_CALL_PATTERN.findall(text)
        for tc_json in tool_calls:
            try:
                tc = json.loads(tc_json)
            except json.JSONDecodeError:
                errors.append("invalid_tool_call_json")
                continue

            name = tc.get("name")
            if not name:
                errors.append("tool_call_missing_name")
                continue

            if self.tool_names and name not in self.tool_names:
                warnings.append(f"unknown_tool:{name}")
                # Don't block — generators may use slightly different names

            args = tc.get("arguments")
            if args is None:
                errors.append("tool_call_missing_arguments")
                continue

            # Validate required arguments
            if name in self.tool_schemas:
                schema = self.tool_schemas[name]
                params = schema.get("parameters", {})
                required = params.get("required", [])
                for req in required:
                    if req not in args:
                        errors.append(f"missing_required_arg:{name}.{req}")

        # Validate tool responses
        tool_responses = TOOL_RESPONSE_PATTERN.findall(text)
        for tr_json in tool_responses:
            try:
                json.loads(tr_json)
            except json.JSONDecodeError:
                errors.append("invalid_tool_response_json")

        # Check tool call / response pairing
        if len(tool_calls) != len(tool_responses):
            warnings.append(f"tool_call_response_mismatch:{len(tool_calls)}calls/{len(tool_responses)}responses")

        # Minimum length check
        if len(text) < 200:
            warnings.append("very_short_example")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def is_duplicate(self, example: dict) -> bool:
        """Check if this example is a near-duplicate of one already seen."""
        text = example.get("text", "")
        # Hash full conversation content (excluding system prompt which is always the same)
        # This preserves examples with same user prompt but different tool call values
        parts = re.findall(r"<\|im_start\|>(?:user|assistant|tool)\n(.*?)\n<\|im_end\|>", text, re.DOTALL)
        dedup_key = "||".join(parts).strip()
        content_hash = hashlib.md5(dedup_key.encode()).hexdigest()

        if content_hash in self._seen_hashes:
            return True
        self._seen_hashes.add(content_hash)
        return False

    def validate_file(self, input_path: Path, output_path: Path | None = None) -> ValidationReport:
        """Validate an entire JSONL file. Optionally write valid examples to output."""
        report = ValidationReport()
        valid_examples = []

        with open(input_path) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                report.total += 1

                try:
                    example = json.loads(line)
                except json.JSONDecodeError:
                    report.invalid += 1
                    report.errors_by_type["invalid_json_line"] = report.errors_by_type.get("invalid_json_line", 0) + 1
                    continue

                if self.is_duplicate(example):
                    report.duplicates_removed += 1
                    continue

                result = self.validate_example(example)
                if result.valid:
                    report.valid += 1
                    valid_examples.append(example)
                else:
                    report.invalid += 1
                    for err in result.errors:
                        err_type = err.split(":")[0]
                        report.errors_by_type[err_type] = report.errors_by_type.get(err_type, 0) + 1

                if line_num % 10000 == 0:
                    logger.info(f"Validated {line_num} examples...")

        if output_path and valid_examples:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                for ex in valid_examples:
                    f.write(json.dumps(ex) + "\n")
            logger.info(f"Wrote {len(valid_examples)} valid examples to {output_path}")

        return report

    def reset(self):
        """Reset deduplication state for a new validation run."""
        self._seen_hashes.clear()
