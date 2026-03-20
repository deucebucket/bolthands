"""Configuration for the BoltHands agent."""

from pydantic_settings import BaseSettings


class BoltHandsConfig(BaseSettings):
    """Application configuration loaded from environment variables.

    All fields can be set via BOLTHANDS_ prefixed env vars,
    e.g. BOLTHANDS_LLM_URL, BOLTHANDS_MAX_ITERATIONS.
    """

    model_config = {"env_prefix": "BOLTHANDS_"}

    llm_url: str = "http://localhost:8080/v1"
    max_iterations: int = 25
    max_output_length: int = 10000
    stuck_threshold: int = 3
    sandbox_memory: str = "4g"
    sandbox_image: str = "python:3.12-slim"
