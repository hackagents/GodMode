from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GEMINI_API_KEY: str
    MODEL_NAME: str = "gemini-3-flash-preview"
    MAX_CHAPTERS: int = 10
    CATALOG_DB_PATH: str = "catalog.db"

    class Config:
        env_file = ".env"


settings = Settings()
