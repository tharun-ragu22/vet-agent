from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_ai.models.google import GoogleModel
from dotenv import load_dotenv
import os

load_dotenv()

gemma_model = OllamaModel(
    model_name=os.getenv("LOCAL_MODEL_NAME"),
    provider=OllamaProvider(
        base_url=os.getenv("LOCAL_MODEL_URL"),
    ),
)

google_model = GoogleModel(
    "gemini-3.5-flash"
)