from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GCP_PROJECT: str
    GCP_LOCATION: str = "global"
    MODEL_NAME: str = "gemini-2.0-flash"
    MAX_CHAPTERS: int = 10
    DATABASE_URL: str
    IMAGEN_MODEL: str = "imagen-4.0-fast-generate-001"

    class Config:
        env_file = ".env"


settings = Settings()
