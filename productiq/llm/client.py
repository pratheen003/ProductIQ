"""
ProductIQ Multi-Provider LLM Client
====================================
Clean abstraction supporting both Groq (primary) and OpenAI (optional).

Design principles:
- API keys are ALWAYS sourced from environment variables (GROQ_API_KEY, OPENAI_API_KEY, LLM_API_KEY).
- Never hard-code API keys. Never log API keys.
- Vendor-agnostic interface: ProductIQ business logic depends ONLY on LLMClient.
- Phase 4 enrichment logic lives in productiq.enrichment, using this abstraction.
"""
import json
import logging
import re
import time
from typing import Any, Optional

from productiq.config import Config, load_config

logger = logging.getLogger("productiq.llm")


class LLMError(Exception):
    """Base exception for LLM client errors."""


class LLMAuthError(LLMError):
    """Raised when the API key is missing or invalid."""


class LLMConnectionError(LLMError):
    """Raised when the API is unreachable or times out."""


class LLMQuotaError(LLMError):
    """Raised when the API quota or credits are exhausted (HTTP 429)."""
    BILLING_URL = "https://platform.openai.com/settings/organization/billing/"


class LLMRateLimitError(LLMError):
    """Raised when API rate limits are exceeded."""


class LLMClient:
    """
    Multi-provider wrapper around Groq and OpenAI APIs.

    Usage:
        client = LLMClient()
        response = client.call("Hello")
        json_obj = client.call_json("Return JSON: ...")
    """

    def __init__(self, config: Optional[Config] = None):
        self._config = config or load_config()
        self._provider = self._config.llm_provider.lower().strip()
        api_key = self._config.active_api_key

        if not api_key:
            key_var = "GROQ_API_KEY" if self._provider == "groq" else "OPENAI_API_KEY / LLM_API_KEY"
            raise LLMAuthError(
                f"{key_var} environment variable is not set for provider '{self._provider}'. "
                f"Copy .env.example to .env and configure your API key."
            )

        self._model = self._config.llm_model
        self._timeout = float(self._config.llm_timeout_seconds)

        if self._provider == "groq":
            try:
                from groq import Groq
                self._client = Groq(api_key=api_key, timeout=self._timeout)
            except ImportError:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=api_key,
                    base_url="https://api.groq.com/openai/v1",
                    timeout=self._timeout,
                )
        elif self._provider == "openai":
            from openai import OpenAI
            self._client = OpenAI(api_key=api_key, timeout=self._timeout)
        else:
            raise LLMError(f"Unsupported LLM provider: '{self._provider}'. Supported: 'groq', 'openai'")

        logger.info(
            "LLMClient initialized | provider=%s | model=%s | timeout=%ds",
            self._provider,
            self._model,
            int(self._timeout),
        )

    @property
    def provider(self) -> str:
        """Active LLM provider name."""
        return self._provider

    @property
    def model(self) -> str:
        """Active model name."""
        return self._model

    def call(
        self,
        prompt: str,
        system: str = "You are a helpful assistant.",
        response_format: Optional[dict] = None,
        max_tokens: int = 3500,
        max_retries: int = 3,
    ) -> str:
        """
        Send a prompt to the LLM and return the text response.
        Includes automatic retry for rate limit pauses.
        """
        logger.debug("LLM call | provider=%s | model=%s | prompt_len=%d", self._provider, self._model, len(prompt))

        kwargs: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "max_tokens": max_tokens,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format

        last_exc: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            try:
                response = self._client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content or ""
                logger.debug("LLM response received | length=%d", len(content))
                return content
            except Exception as exc:
                last_exc = exc
                exc_str = str(exc).lower()
                if ("rate_limit" in exc_str or "429" in exc_str) and "insufficient_quota" not in exc_str and attempt < max_retries:
                    wait_s = 4.0 * (attempt + 1)
                    match = re.search(r"try again in ([\d\.]+)s", str(exc), re.IGNORECASE)
                    if match:
                        try:
                            wait_s = float(match.group(1)) + 0.5
                        except ValueError:
                            pass
                    logger.warning("Rate limit hit (attempt %d/%d). Backing off for %.1fs...", attempt + 1, max_retries, wait_s)
                    time.sleep(wait_s)
                    continue

                if "json_validate_failed" in exc_str and attempt < max_retries:
                    # Retry without strict json response_format if provider parser glitched
                    kwargs.pop("response_format", None)
                    time.sleep(1.0)
                    continue

                self._handle_exception(exc)
                raise

        if last_exc:
            self._handle_exception(last_exc)
        raise LLMError("LLM call failed after retries")

    def call_json(self, prompt: str, system: str = "You are a helpful assistant.") -> Any:
        """
        Send a prompt and parse the response as JSON.
        Uses json_object response format where supported, with fallback parsing.
        """
        raw = self.call(prompt=prompt, system=system, response_format={"type": "json_object"}, max_tokens=3500)

        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
        cleaned = cleaned.strip()

        # Try direct parse
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Fallback: Extract outermost JSON object {...}
        match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        raise LLMError(f"LLM returned non-JSON response: {cleaned[:300]}")

    def ping(self) -> dict:
        """
        Connectivity proof test.
        Sends a trivial JSON request and validates the response.
        """
        logger.info("LLM ping test starting on provider=%s...", self._provider)
        result = self.call_json(
            prompt='Return exactly this JSON object and nothing else: {"status": "ok", "system": "ProductIQ"}',
            system="You are a JSON-only responder. Return only valid JSON, no markdown, no explanation.",
        )
        if not isinstance(result, dict):
            raise LLMError(f"Ping response is not a JSON object: {result}")
        logger.info("LLM ping succeeded | provider=%s | model=%s", self._provider, self._model)
        return result

    def _handle_exception(self, exc: Exception) -> None:
        """Normalize vendor exceptions into standard ProductIQ LLM exceptions."""
        exc_name = exc.__class__.__name__
        exc_str = str(exc)

        if "Authentication" in exc_name or "auth" in exc_str.lower() or "401" in exc_str:
            raise LLMAuthError(f"Authentication failed for provider '{self._provider}': {exc}") from exc

        if "RateLimit" in exc_name or "429" in exc_str:
            if "insufficient_quota" in exc_str or "credit_balance" in exc_str:
                raise LLMQuotaError(f"Quota/credit exhausted for provider '{self._provider}': {exc}") from exc
            raise LLMRateLimitError(f"Rate limit exceeded for provider '{self._provider}': {exc}") from exc

        if "Timeout" in exc_name or "timed out" in exc_str.lower():
            raise LLMConnectionError(f"LLM API timed out after {int(self._timeout)}s: {exc}") from exc

        if "Connection" in exc_name or "unreachable" in exc_str.lower():
            raise LLMConnectionError(f"LLM API connection failed for provider '{self._provider}': {exc}") from exc

        raise LLMError(f"LLM call failed ({self._provider}): {exc}") from exc
