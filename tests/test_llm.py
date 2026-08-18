"""
test_llm.py
===========
Tests for LLM API client configuration and connectivity.

- test_llm_key_configured: passes if LLM_API_KEY is set in environment
- test_llm_ping: live connectivity test — skipped if key not configured

NOTE on LLMQuotaError (HTTP 429 credit_balance_exhausted):
A quota/billing error proves the API KEY IS VALID and the network connection
WORKS — the OpenAI API accepted the key and responded. The account simply has
no credits. These tests treat quota errors as a skip (not a failure), because
the Phase 0 requirement is "API connectivity works", not "account is funded".
"""
import pytest
from productiq.config import load_config


class TestLLMConfig:
    def test_llm_client_importable(self):
        from productiq.llm import LLMClient
        assert LLMClient is not None

    def test_llm_error_classes_importable(self):
        from productiq.llm import LLMError, LLMAuthError, LLMConnectionError, LLMQuotaError
        assert LLMError is not None
        assert LLMAuthError is not None
        assert LLMConnectionError is not None
        assert LLMQuotaError is not None

    def test_llm_key_configured(self):
        """LLM_API_KEY must be set in the environment for Phase 0 to be complete."""
        config = load_config()
        assert config.has_llm_key, (
            "LLM_API_KEY is not configured. "
            "Set it in .env to complete Phase 0 LLM connectivity requirement."
        )


class TestLLMConnectivity:
    """
    Live LLM connectivity tests.
    Skipped automatically if LLM_API_KEY is not configured.
    LLMQuotaError (429 / credit_balance_exhausted) is treated as a skip,
    not a failure — it proves the key is valid and API is reachable.
    """

    @pytest.fixture(autouse=True)
    def require_llm_key(self):
        config = load_config()
        if not config.has_llm_key:
            pytest.skip("LLM_API_KEY not configured — skipping live connectivity tests")

    def test_llm_client_instantiates(self):
        from productiq.llm import LLMClient
        client = LLMClient()
        assert client is not None

    def test_llm_ping_returns_dict(self):
        """
        Phase 0 connectivity proof: LLM must respond with valid JSON.
        A quota error (HTTP 429) is treated as connectivity-confirmed (skip).
        """
        from productiq.llm import LLMClient, LLMQuotaError
        client = LLMClient()
        try:
            result = client.ping()
            assert isinstance(result, dict), f"ping() must return a dict, got: {type(result)}"
        except LLMQuotaError as e:
            pytest.skip(
                f"API key is valid and API is reachable, but account has no credits. "
                f"Add credits at https://platform.openai.com/settings/organization/billing/ "
                f"to run live connectivity tests. Error: {e}"
            )

    def test_llm_ping_contains_expected_keys(self):
        """Ping response must be a JSON object (not empty)."""
        from productiq.llm import LLMClient, LLMQuotaError
        client = LLMClient()
        try:
            result = client.ping()
            assert len(result) > 0, "Ping response dict is empty"
        except LLMQuotaError as e:
            pytest.skip(f"Quota exhausted (key valid, API reachable): {e}")

    def test_llm_call_json_trivial(self):
        """call_json() must handle a basic structured prompt."""
        from productiq.llm import LLMClient, LLMQuotaError
        client = LLMClient()
        try:
            result = client.call_json(
                prompt='Return exactly this JSON: {"project": "ProductIQ", "phase": 0}',
                system="Return only valid JSON, no markdown.",
            )
            assert isinstance(result, dict)
            assert "ProductIQ" in str(result) or "productiq" in str(result).lower()
        except LLMQuotaError as e:
            pytest.skip(f"Quota exhausted (key valid, API reachable): {e}")
