"""
ProductIQ Configuration
-----------------------
Loads environment variables from .env file.
Never logs or exposes API keys.
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

    @property
    def has_llm_key(self) -> bool:
        return bool(self.llm_api_key)


def load_config() -> Config:
    """Load and return the application configuration from environment variables."""
    return Config(
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        llm_timeout_seconds=int(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        data_dir=os.getenv(
            "DATA_DIR",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"),
        ),
    )
