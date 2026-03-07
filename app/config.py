from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    pinchtab_url: str = "http://localhost:9867"
    download_dir: str = "downloads"
    max_workers: int = 15
    request_timeout: int = 30
    retry_attempts: int = 4
    cache_db: str = "cache.db"
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
