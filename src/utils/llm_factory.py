from typing import Literal, Optional, Any
import os
import logging
from pydantic import BaseModel, SecretStr
from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger(__name__)

class AgentLLMConfig(BaseModel):
    """
    Decouples agent logic from model provider.
    Provides a plug-and-play interface for LLM instantiation.
    """
    provider: Literal["groq", "openai", "vertex", "google_genai"]
    model: str
    temperature: float = 0.0
    max_tokens: Optional[int] = 4096

    def get_chat_model(self, **kwargs: Any) -> BaseChatModel:
        """Returns the appropriate LangChain chat model based on the configuration."""
        if self.provider == "groq":
            from langchain_groq import ChatGroq
            api_key = os.getenv("GROQ_API_KEY", "")
            if not api_key:
                logger.warning("GROQ_API_KEY is not set.")
            return ChatGroq(
                api_key=SecretStr(api_key),
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                **kwargs
            )

        elif self.provider == "openai":
            from langchain_openai import ChatOpenAI
            api_key = os.getenv("OPENAI_API_KEY", "")
            if not api_key:
                logger.warning("OPENAI_API_KEY is not set.")
            return ChatOpenAI(
                api_key=SecretStr(api_key),
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                **kwargs
            )

        elif self.provider == "vertex":
            from langchain_google_vertexai import ChatVertexAI
            project = os.getenv("PROJECT_ID")
            location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

            return ChatVertexAI(
                model_name=self.model,
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
                project=project,
                location=location,
                **kwargs
            )

        elif self.provider == "google_genai":
            # Newer unified SDK — handles both API key and Vertex AI auth.
            # Recommended by LangChain for Gemini 3.x+ models.
            from langchain_google_genai import ChatGoogleGenerativeAI
            project = os.getenv("PROJECT_ID")
            location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

            return ChatGoogleGenerativeAI(
                model=self.model,
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
                max_retries=2,
                project=project,
                location=location,
                **kwargs
            )

        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
