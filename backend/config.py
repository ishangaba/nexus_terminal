from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    alpha_vantage_api_key: str = ""
    finnhub_api_key: str = ""
    anthropic_api_key: str = ""
    arcadedb_url: str = "http://localhost:2480"
    arcadedb_database: str = "nexus_graph"
    arcadedb_user: str = "root"
    arcadedb_password: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
