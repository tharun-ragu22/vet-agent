from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.models.google import GoogleModel
from dotenv import load_dotenv
import os

load_dotenv()

gemma_model = OllamaModel(
    model_name="gemma4:latest",
    provider=OllamaProvider(base_url="http://localhost:11434/v1"),
)

openrouter_model = OpenRouterModel(
    "google/gemma-4-26b-a4b-it:free",
)

google_model = GoogleModel(
    "gemini-3.5-flash"
)