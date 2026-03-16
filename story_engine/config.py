from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GEMINI_API_KEY: str
    MODEL_NAME: str = "gemini-3-flash-preview"
    MAX_CHAPTERS: int = 10
    CATALOG_DB_PATH: str = "catalog.db"
    
    # Vertex AI / Imagen Settings
    GOOGLE_CLOUD_PROJECT: str = "YOUR_PROJECT_ID"
    GOOGLE_CLOUD_LOCATION: str = "us-central1"

    class Config:
        env_file = ".env"


settings = Settings()
