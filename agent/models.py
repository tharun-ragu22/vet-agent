from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_ai.models.google import GoogleModel
from dotenv import load_dotenv

load_dotenv()

gemma_model = OllamaModel(
    model_name="gemma4:latest",
    provider=OllamaProvider(base_url="http://localhost:11434/v1"),
)

google_model = GoogleModel(
    "gemini-3.5-flash"
)