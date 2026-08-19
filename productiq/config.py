"""
ProductIQ Configuration
-----------------------
Loads environment variables from .env file.
Never logs or exposes API keys.
Supports multi-provider LLM configuration (Groq, OpenAI).
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load .env from the project root (parent of this file's package dir)
_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path=_env_path, override=False)


@dataclass(frozen=True)
class Config:
    """Immutable configuration object for ProductIQ."""
    llm_api_key: str
    llm_model: str
    llm_timeout_seconds: int
    log_level: str
    data_dir: str
    llm_provider: str = "groq"
    groq_api_key: str = ""
    openai_api_key: str = ""

    @property
    def has_llm_key(self) -> bool:
        """Returns True if the active provider has an API key configured."""
        if self.llm_provider == "groq":
            return bool(self.groq_api_key or self.llm_api_key)
        elif self.llm_provider == "openai":
            return bool(self.openai_api_key or self.llm_api_key)
        return bool(self.llm_api_key or self.groq_api_key or self.openai_api_key)

    @property
    def active_api_key(self) -> str:
        """Return the API key for the active provider."""
        if self.llm_provider == "groq":
            return self.groq_api_key or self.llm_api_key
        elif self.llm_provider == "openai":
            return self.openai_api_key or self.llm_api_key
        return self.llm_api_key


def load_config() -> Config:
    """Load and return the application configuration from environment variables."""
    groq_key = os.getenv("GROQ_API_KEY", "")
    openai_key = os.getenv("OPENAI_API_KEY", "")
    generic_llm_key = os.getenv("LLM_API_KEY", "")

    # Provider selection
    provider = os.getenv("LLM_PROVIDER", "").lower().strip()
    if not provider:
        # Auto-detect: prefer Groq if GROQ_API_KEY is present
        if groq_key:
            provider = "groq"
        elif openai_key or generic_llm_key:
            provider = "openai"
        else:
            provider = "groq"

    # Default model selection per provider
    default_model = "openai/gpt-oss-20b" if provider == "groq" else "gpt-4o-mini"
    model = os.getenv("LLM_MODEL", default_model)

    # Active API key
    active_key = groq_key if provider == "groq" else (openai_key or generic_llm_key)
    if not active_key and generic_llm_key:
        active_key = generic_llm_key

    return Config(
        llm_api_key=active_key,
        llm_model=model,
        llm_timeout_seconds=int(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        data_dir=os.getenv(
            "DATA_DIR",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"),
        ),
        llm_provider=provider,
        groq_api_key=groq_key,
        openai_api_key=openai_key,
    )
