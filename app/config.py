from __future__ import annotations
import os
from enum import Enum
from typing import Dict, List
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.utils.yaml_config import YamlConfigSettingsSource

class TaskType(Enum):
    META_OPTIMIZATION = "meta_optimization"
    CONTENT_REWRITING = "content_rewriting"
    KEYWORD_ANALYSIS = "keyword_analysis"
    SCHEMA_ANALYSIS = "schema_analysis"
    CATEGORY_NORMALIZATION = "category_normalization"
    TAG_OPTIMIZATION = "tag_optimization"

class Settings(BaseSettings):
    ollama: Ollama = Ollama()
    models: Models
    paths: Paths
    categories: Categories
    fields: Fields
    pipeline: Pipeline
    workers: Workers
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
