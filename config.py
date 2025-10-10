from pydantic_settings import BaseSettings, SettingsConfigDict, YamlConfigSettingsSource
from pydantic import BaseModel
from typing import ClassVar, List, Dict, Any
from enum import Enum

class TaskType(Enum):
    META_OPTIMIZATION = "meta_optimization"
    CONTENT_REWRITING = "content_rewriting" 
    KEYWORD_ANALYSIS = "keyword_analysis"
    SCHEMA_ANALYSIS = "schema_analysis"

class ModelConfig(BaseModel):
    tasks: List[TaskType]
    description: str
    max_tokens: int

class ModelCapabilities(BaseModel):
    capabilities: Dict[str, ModelConfig]
    fallback_order: List[str]

import os

class Ollama(BaseModel):
    host: str = os.getenv("OLLAMA_HOST", "http://localhost").rstrip('/')
    port: int = 11434
    
    @property
    def base_url(self) -> str:
        # If host already includes port, return as is
        if ':' in self.host.split('//')[-1]:
            return self.host
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

class Settings(BaseSettings):
    ollama: Ollama = Ollama()
    models: Models
    paths: Paths
    categories: Categories
    fields: Fields
    pipeline: Pipeline
    model_capabilities: ModelCapabilities

    model_config = SettingsConfigDict(yaml_file="config.yaml")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: "SettingsDict",
        env_settings: "SettingsDict",
        dotenv_settings: "SettingsDict",
        file_secret_settings: "SettingsDict",
    ) -> tuple["SourceCallable", ...]:
        return (
            env_settings,
            YamlConfigSettingsSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )

settings = Settings()
