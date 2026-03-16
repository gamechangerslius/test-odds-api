from functools import lru_cache

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    opticodds_api_key: str
    opticodds_base_url: AnyHttpUrl

    default_sport: str = "soccer"
    default_market: str = "moneyline"
    default_sportsbooks: list[str] = ["DraftKings"]

    request_timeout_seconds: float = 5.0

    class Config:
        env_file = ".env"
        env_prefix = ""
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
