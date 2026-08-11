from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    alpha_vantage_api_key: str = ""
    finnhub_api_key: str = ""
    anthropic_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
