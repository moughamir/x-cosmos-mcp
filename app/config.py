import os
from enum import Enum
from typing import Any, Callable, Dict, List, Tuple

from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, YamlConfigSettingsSource


class TaskType(Enum):
    META_OPTIMIZATION = "meta_optimization"
    CONTENT_REWRITING = "content_rewriting"
    KEYWORD_ANALYSIS = "keyword_analysis"
    SCHEMA_ANALYSIS = "schema_analysis"
    CATEGORY_NORMALIZATION = "category_normalization"
    TAG_OPTIMIZATION = "tag_optimization"


class ModelConfig(BaseModel):
    tasks: List[TaskType]
    description: str
    max_tokens: int

    @field_validator("tasks", mode="before")
    @classmethod
    def convert_tasks_to_enum(cls, v):
        if isinstance(v, list):
            return [TaskType(task_str) for task_str in v]
        return v


class ModelCapabilities(BaseModel):
    capabilities: Dict[str, ModelConfig]
    fallback_order: List[str]


class Ollama(BaseModel):
    host: str = "http://localhost"
    port: int = 11434

    @property
    def base_url(self) -> str:
        return f"{self.host}:{self.port}"

    @property
    def api_url(self) -> str:
        return f"{self.base_url}/api"


class Models(BaseModel):
    title_model: str
    description_model: str
    provider: str
    temperature: float
    max_output_tokens: int
    concurrency: int
    batch_size: int
    timeout: int
    quantized_models: Dict[str, str] = {}  # Map of model -> quantized version


class Paths(BaseModel):
    database: str
    log_table: str
    prompt_dir: str
    static_dir: str = "views/admin/static"


class Categories(BaseModel):
    taxonomy_source: str
    taxonomy_url: str


class Fields(BaseModel):
    process: List[str]


class Pipeline(BaseModel):
    steps: List[str]


class Postgres(BaseModel):
    host: str = os.getenv("POSTGRES_HOST", "postgres")
    port: int = int(os.getenv("POSTGRES_PORT", 5432))
    user: str = os.getenv("POSTGRES_USER", "mcp_user")
    password: str = os.getenv("POSTGRES_PASSWORD", "mcp_password")
    database: str = os.getenv("POSTGRES_DB", "mcp_db")


class Workers(BaseModel):
    max_workers: int
    queue_size: int
    timeout: int
    retry_attempts: int
    batch_size: int


class Settings(BaseSettings):
    ollama: Ollama = Ollama()
    models: Models
    quantized_models: Dict[str, str]
    paths: Paths
    categories: Categories
    fields: Fields
    pipeline: Pipeline
    workers: Workers
    postgres: Postgres
    model_capabilities: ModelCapabilities

    model_config = SettingsConfigDict(yaml_file="config.yaml")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: Any,
        env_settings: Any,
        dotenv_settings: Any,
        file_secret_settings: Any,
    ) -> Tuple[Callable[..., Any], ...]:
        return (
            env_settings,
            YamlConfigSettingsSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )


settings = Settings()
