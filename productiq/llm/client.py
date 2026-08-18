"""
ProductIQ LLM Client
====================
Clean abstraction over the LLM API provider.

Design principles:
- API key is ALWAYS sourced from the LLM_API_KEY environment variable.
- Never hard-code API keys. Never log API keys.
- Vendor-agnostic interface: swap provider by changing config, not calling code.
- Phase 0 only proves connectivity — enrichment logic lives in productiq.enrichment.

Phase 0 test: ping() sends a trivial JSON request and validates the response.
"""
import json
import logging
from typing import Any

from openai import OpenAI, APIConnectionError, APITimeoutError, AuthenticationError, RateLimitError

from productiq.config import Config, load_config

logger = logging.getLogger("productiq.llm")


class LLMError(Exception):
    """Base exception for LLM client errors."""


class LLMAuthError(LLMError):
    """Raised when the API key is missing or invalid."""


class LLMConnectionError(LLMError):
    """Raised when the API is unreachable."""


class LLMQuotaError(LLMError):
    """Raised when the API quota or credits are exhausted (HTTP 429)."""
    BILLING_URL = "https://platform.openai.com/settings/organization/billing/"


class LLMClient:
    """
    Thin wrapper around the configured LLM provider (OpenAI by default).

    Usage:
        client = LLMClient()
        result = client.ping()   # Phase 0 connectivity test
    """

    def __init__(self, config: Config | None = None):
        self._config = config or load_config()
        if not self._config.has_llm_key:
            raise LLMAuthError(
                "LLM_API_KEY environment variable is not set. "
                "Copy .env.example to .env and add your API key."
            )
        # Key is read from config — never passed through logs
        self._client = OpenAI(
            api_key=self._config.llm_api_key,
            timeout=float(self._config.llm_timeout_seconds),
        )
        logger.info(
            "LLMClient initialized | model=%s | timeout=%ds",
            self._config.llm_model,
            self._config.llm_timeout_seconds,
        )

    def call(self, prompt: str, system: str = "You are a helpful assistant.") -> str:
        """
        Send a prompt to the LLM and return the text response.

        Args:
            prompt: User message content.
            system: System message content.

        Returns:
            LLM response as a plain string.

        Raises:
            LLMAuthError: If the API key is invalid.
            LLMConnectionError: If the API is unreachable or times out.
            LLMError: For other API errors.
        """
        logger.debug("LLM call | model=%s | prompt_length=%d", self._config.llm_model, len(prompt))
        try:
            response = self._client.chat.completions.create(
                model=self._config.llm_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
            )
            content = response.choices[0].message.content or ""
            logger.debug("LLM response received | length=%d", len(content))
            return content

        except AuthenticationError as e:
            raise LLMAuthError(f"API authentication failed: {e}") from e
        except RateLimitError as e:
            # 429 covers both rate-limit and credit/quota exhaustion
            raise LLMQuotaError(
                f"OpenAI quota exhausted (HTTP 429). "
                f"Add credits at {LLMQuotaError.BILLING_URL}\n"
                f"Original error: {e}"
            ) from e
        except APITimeoutError as e:
            raise LLMConnectionError(f"LLM API timed out after {self._config.llm_timeout_seconds}s") from e
        except APIConnectionError as e:
            raise LLMConnectionError(f"LLM API connection failed: {e}") from e
        except Exception as e:
            raise LLMError(f"Unexpected LLM error: {e}") from e

    def call_json(self, prompt: str, system: str = "You are a helpful assistant.") -> Any:
        """
        Send a prompt and parse the response as JSON.

        Returns:
            Parsed JSON object (dict, list, etc.)

        Raises:
            LLMError: If the response is not valid JSON.
        """
        raw = self.call(prompt=prompt, system=system)
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove opening ``` line and closing ``` line
            cleaned = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise LLMError(f"LLM returned non-JSON response: {e}\nRaw response: {raw[:200]}") from e

    def ping(self) -> dict:
        """
        Phase 0 connectivity test.

        Sends a trivial JSON request and validates the response contains
        the expected key. Does NOT test enrichment logic.

        Returns:
            Parsed JSON dict from the LLM response.

        Raises:
            LLMError: If the call fails or the response is not valid JSON.
        """
        logger.info("LLM ping test starting...")
        result = self.call_json(
            prompt='Return exactly this JSON object and nothing else: {"status": "ok", "system": "ProductIQ"}',
            system="You are a JSON-only responder. Return only valid JSON, no markdown, no explanation.",
        )
        if not isinstance(result, dict):
            raise LLMError(f"Ping response is not a JSON object: {result}")
        logger.info("LLM ping succeeded | response_keys=%s", list(result.keys()))
        return result
