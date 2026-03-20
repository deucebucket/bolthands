"""Tests for event models: serialization, deserialization, discriminated unions."""

import pytest
from pydantic import TypeAdapter, ValidationError

from bolthands.events import (
    Action,
    CmdRunAction,
    FileEditAction,
    FileReadAction,
    FileWriteAction,
    FinishAction,
    SearchFilesAction,
    ThinkAction,
)
from bolthands.events import (
    CmdOutputObservation,
    ErrorObservation,
    FileContentObservation,
    FileEditObservation,
    FileWriteObservation,
    Observation,
    SearchResultObservation,
    ThinkObservation,
)


# ---------------------------------------------------------------------------
# Action serialization / deserialization
# ---------------------------------------------------------------------------

class TestActionModels:
    def test_cmd_run_defaults(self):
        a = CmdRunAction(command="ls -la")
        assert a.type == "cmd_run"
        assert a.command == "ls -la"
        assert a.timeout == 30

    def test_cmd_run_custom_timeout(self):
        a = CmdRunAction(command="make build", timeout=120)
        assert a.timeout == 120

    def test_file_read_defaults(self):
        a = FileReadAction(path="/workspace/main.py")
        assert a.type == "file_read"
        assert a.max_lines is None

    def test_file_read_with_max_lines(self):
        a = FileReadAction(path="/workspace/main.py", max_lines=50)
        assert a.max_lines == 50

    def test_file_write(self):
        a = FileWriteAction(path="/workspace/out.txt", content="hello")
        assert a.type == "file_write"
        assert a.content == "hello"

    def test_file_edit(self):
        a = FileEditAction(path="/workspace/f.py", old_str="foo", new_str="bar")
        assert a.type == "file_edit"
        assert a.old_str == "foo"
        assert a.new_str == "bar"

    def test_search_files_defaults(self):
        a = SearchFilesAction(pattern="TODO")
        assert a.path == "."
        assert a.max_results == 20

    def test_think(self):
        a = ThinkAction(thought="I should check the logs")
        assert a.type == "think"

    def test_finish(self):
        a = FinishAction(message="Done")
        assert a.type == "finish"

    def test_roundtrip_serialization(self):
        a = CmdRunAction(command="echo hi", timeout=10)
        data = a.model_dump()
        assert data == {"type": "cmd_run", "command": "echo hi", "timeout": 10}
        restored = CmdRunAction.model_validate(data)
        assert restored == a

    def test_json_roundtrip(self):
        a = FileEditAction(path="x.py", old_str="a", new_str="b")
        json_str = a.model_dump_json()
        restored = FileEditAction.model_validate_json(json_str)
        assert restored == a


# ---------------------------------------------------------------------------
# Observation serialization / deserialization
# ---------------------------------------------------------------------------

class TestObservationModels:
    def test_cmd_output(self):
        o = CmdOutputObservation(stdout="hello\n", stderr="", exit_code=0)
        assert o.type == "cmd_output"
        assert o.exit_code == 0

    def test_file_content(self):
        o = FileContentObservation(path="f.py", content="x = 1", exists=True)
        assert o.type == "file_content"

    def test_file_write_result_success(self):
        o = FileWriteObservation(path="f.py", success=True)
        assert o.error is None

    def test_file_write_result_failure(self):
        o = FileWriteObservation(path="f.py", success=False, error="permission denied")
        assert o.error == "permission denied"

    def test_file_edit_result(self):
        o = FileEditObservation(path="f.py", success=True)
        assert o.type == "file_edit_result"

    def test_search_result(self):
        o = SearchResultObservation(matches=["a.py:1:foo"], total_count=1)
        assert o.type == "search_result"
        assert len(o.matches) == 1

    def test_think_observation(self):
        o = ThinkObservation(thought="noted")
        assert o.type == "think_result"

    def test_error_observation(self):
        o = ErrorObservation(error_type="timeout", message="command timed out")
        assert o.type == "error"

    def test_roundtrip_serialization(self):
        o = CmdOutputObservation(stdout="ok", stderr="warn", exit_code=1)
        data = o.model_dump()
        restored = CmdOutputObservation.model_validate(data)
        assert restored == o


# ---------------------------------------------------------------------------
# Discriminated union parsing
# ---------------------------------------------------------------------------

ActionAdapter = TypeAdapter(Action)
ObservationAdapter = TypeAdapter(Observation)


class TestDiscriminatedUnions:
    def test_parse_cmd_run_action(self):
        data = {"type": "cmd_run", "command": "pwd"}
        result = ActionAdapter.validate_python(data)
        assert isinstance(result, CmdRunAction)

    def test_parse_file_read_action(self):
        data = {"type": "file_read", "path": "/workspace/x.py"}
        result = ActionAdapter.validate_python(data)
        assert isinstance(result, FileReadAction)

    def test_parse_file_write_action(self):
        data = {"type": "file_write", "path": "x.py", "content": "hi"}
        result = ActionAdapter.validate_python(data)
        assert isinstance(result, FileWriteAction)

    def test_parse_file_edit_action(self):
        data = {"type": "file_edit", "path": "x.py", "old_str": "a", "new_str": "b"}
        result = ActionAdapter.validate_python(data)
        assert isinstance(result, FileEditAction)

    def test_parse_search_files_action(self):
        data = {"type": "search_files", "pattern": "def main"}
        result = ActionAdapter.validate_python(data)
        assert isinstance(result, SearchFilesAction)

    def test_parse_think_action(self):
        data = {"type": "think", "thought": "hmm"}
        result = ActionAdapter.validate_python(data)
        assert isinstance(result, ThinkAction)

    def test_parse_finish_action(self):
        data = {"type": "finish", "message": "all done"}
        result = ActionAdapter.validate_python(data)
        assert isinstance(result, FinishAction)

    def test_parse_cmd_output_observation(self):
        data = {"type": "cmd_output", "stdout": "", "stderr": "", "exit_code": 0}
        result = ObservationAdapter.validate_python(data)
        assert isinstance(result, CmdOutputObservation)

    def test_parse_error_observation(self):
        data = {"type": "error", "error_type": "runtime", "message": "boom"}
        result = ObservationAdapter.validate_python(data)
        assert isinstance(result, ErrorObservation)

    def test_invalid_type_raises(self):
        data = {"type": "nonexistent", "foo": "bar"}
        with pytest.raises(ValidationError):
            ActionAdapter.validate_python(data)

    def test_missing_required_field_raises(self):
        data = {"type": "cmd_run"}  # missing 'command'
        with pytest.raises(ValidationError):
            ActionAdapter.validate_python(data)

    def test_action_from_json(self):
        import json
        data = json.dumps({"type": "finish", "message": "done"})
        result = ActionAdapter.validate_json(data)
        assert isinstance(result, FinishAction)

    def test_observation_from_json(self):
        import json
        data = json.dumps({"type": "search_result", "matches": ["a.py"], "total_count": 1})
        result = ObservationAdapter.validate_json(data)
        assert isinstance(result, SearchResultObservation)
