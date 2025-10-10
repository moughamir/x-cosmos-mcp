from pydantic_settings import BaseSettings, SettingsConfigDict, YamlConfigSettingsSource
from pydantic import BaseModel
from typing import ClassVar, List

class Ollama(BaseModel):
    host: str = "http://localhost"
    port: int = 11434

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
