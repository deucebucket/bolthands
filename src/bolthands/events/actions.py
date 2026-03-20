"""Action models for the BoltHands agent loop.

Each action represents a request from the LLM to perform an operation
in the sandbox environment.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class CmdRunAction(BaseModel):
    type: Literal["cmd_run"] = "cmd_run"
    command: str
    timeout: int = 30


class FileReadAction(BaseModel):
    type: Literal["file_read"] = "file_read"
    path: str
    max_lines: int | None = None


class FileWriteAction(BaseModel):
    type: Literal["file_write"] = "file_write"
    path: str
    content: str


class FileEditAction(BaseModel):
    type: Literal["file_edit"] = "file_edit"
    path: str
    old_str: str
    new_str: str


class SearchFilesAction(BaseModel):
    type: Literal["search_files"] = "search_files"
    pattern: str
    path: str = "."
    max_results: int = 20


class ThinkAction(BaseModel):
    type: Literal["think"] = "think"
    thought: str


class FinishAction(BaseModel):
    type: Literal["finish"] = "finish"
    message: str


Action = Annotated[
    Union[
        CmdRunAction,
        FileReadAction,
        FileWriteAction,
        FileEditAction,
        SearchFilesAction,
        ThinkAction,
        FinishAction,
    ],
    Field(discriminator="type"),
]
