import os

from google import genai

from story_engine.config import settings

# Configure Vertex AI for both ADK agents and direct genai calls
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
os.environ["GOOGLE_CLOUD_PROJECT"] = settings.GCP_PROJECT
os.environ["GOOGLE_CLOUD_LOCATION"] = settings.GCP_LOCATION

# Direct genai client — used for image generation and STT (non-ADK paths)
gemini_client = genai.Client(
    vertexai=True,
    project=settings.GCP_PROJECT,
    location=settings.GCP_LOCATION,
)
