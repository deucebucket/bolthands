"""Observation models for the BoltHands agent loop.

Each observation represents the result of executing an action
in the sandbox environment.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class CmdOutputObservation(BaseModel):
    type: Literal["cmd_output"] = "cmd_output"
    stdout: str
    stderr: str
    exit_code: int


class FileContentObservation(BaseModel):
    type: Literal["file_content"] = "file_content"
    path: str
    content: str
    exists: bool


class FileWriteObservation(BaseModel):
    type: Literal["file_write_result"] = "file_write_result"
    path: str
    success: bool
    error: str | None = None


class FileEditObservation(BaseModel):
    type: Literal["file_edit_result"] = "file_edit_result"
    path: str
    success: bool
    error: str | None = None


class SearchResultObservation(BaseModel):
    type: Literal["search_result"] = "search_result"
    matches: list[str]
    total_count: int


class ThinkObservation(BaseModel):
    type: Literal["think_result"] = "think_result"
    thought: str


class ErrorObservation(BaseModel):
    type: Literal["error"] = "error"
    error_type: str
    message: str


Observation = Annotated[
    Union[
        CmdOutputObservation,
        FileContentObservation,
        FileWriteObservation,
        FileEditObservation,
        SearchResultObservation,
        ThinkObservation,
        ErrorObservation,
    ],
    Field(discriminator="type"),
]
