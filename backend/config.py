from pydantic_settings import BaseSettings

# Keys the user can plug in from the Settings UI at runtime, without a restart.
USER_CONFIGURABLE_KEYS = ("alpha_vantage_api_key", "finnhub_api_key", "anthropic_api_key", "marketaux_api_key")


class Settings(BaseSettings):
    alpha_vantage_api_key: str = ""
    finnhub_api_key: str = ""
    anthropic_api_key: str = ""
    marketaux_api_key: str = ""
    arcadedb_url: str = "http://localhost:2480"
    arcadedb_database: str = "nexus_graph"
    arcadedb_user: str = "root"
    arcadedb_password: str = ""

    class Config:
        env_file = ".env"


settings = Settings()


def apply_settings_overrides() -> None:
    """Layer DB-stored API keys (set via the Settings UI) on top of the .env defaults."""
    from db.models import get_all_settings

    overrides = get_all_settings()
    for key in USER_CONFIGURABLE_KEYS:
        if key in overrides:
            setattr(settings, key, overrides[key])

    from services import claude_analyst

    claude_analyst.reload_client()
