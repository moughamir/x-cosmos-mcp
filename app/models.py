from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, field_validator

from app.config import TaskType


class Ollama(BaseModel):
    host: str
    port: int

    @property
    def base_url(self) -> str:
        # If host already includes port, return as is
        if ":" in self.host.split("//")[-1]:
            return self.host
        return f"{self.host}:{self.port}"


class Models(BaseModel):
    title_model: str
    description_model: str
    provider: str
    temperature: float
    max_output_tokens: int
    concurrency: int
    batch_size: int
    timeout: int
    quantize: bool = False
    quantized_models: Dict[str, str] = {}


class Paths(BaseModel):
    database: str
    log_table: str
    prompt_dir: str


class Categories(BaseModel):
    taxonomy_source: str
    taxonomy_url: str


class Fields(BaseModel):
    process: List[str]


class Pipeline(BaseModel):
    steps: List[str]


class Workers(BaseModel):
    max_workers: int
    queue_size: int
    timeout: int
    retry_attempts: int
    batch_size: int


class ModelConfig(BaseModel):
    tasks: List[TaskType]
    description: str
    max_tokens: int

    @field_validator("tasks", mode="before")
    @classmethod
    def convert_tasks_to_enum(cls, v):
        """Convert list of strings to TaskType enums"""
        if isinstance(v, list):
            return [TaskType(task_str) for task_str in v]
        return v


class ModelCapabilities(BaseModel):
    capabilities: Dict[str, ModelConfig]
    fallback_order: List[str]
