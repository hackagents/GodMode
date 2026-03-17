from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GEMINI_API_KEY: str
    MODEL_NAME: str = "gemini-3-flash-preview"
    MAX_CHAPTERS: int = 10
    DATABASE_URL: str
    IMAGEN_MODEL: str = "imagen-4.0-fast-generate-001"

    class Config:
        env_file = ".env"


settings = Settings()
