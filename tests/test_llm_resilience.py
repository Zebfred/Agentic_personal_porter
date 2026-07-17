"""
Tests for the centralized LLM Resilience Factory.

Validates that get_resilient_llm() returns a properly configured
three-tier fallback chain with circuit breaking.
"""
import os
import sys
from unittest.mock import patch, MagicMock


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestGetResilientLLM:
    """Tests for the get_resilient_llm factory."""

    @patch("src.utils.llm_resilience.TIER_1_CONFIG")
    @patch("src.utils.llm_resilience.TIER_2_CONFIG")
    @patch("src.utils.llm_resilience.TIER_3_CONFIG")
    def test_returns_model_with_fallbacks(self, mock_t3, mock_t2, mock_t1):
        """Verify the factory returns a model with with_fallbacks applied."""
        from src.utils.llm_resilience import get_resilient_llm

        # Mock each tier's get_chat_model to return a mock LLM
        mock_primary = MagicMock()
        mock_flash = MagicMock()
        mock_pro = MagicMock()
        mock_fallback_chain = MagicMock()

        mock_t1.model_copy.return_value.get_chat_model.return_value = mock_primary
        mock_t2.model_copy.return_value.get_chat_model.return_value = mock_flash
        mock_t3.model_copy.return_value.get_chat_model.return_value = mock_pro

        mock_primary.with_fallbacks.return_value = mock_fallback_chain

        result = get_resilient_llm(task="test_agent")

        # Verify with_fallbacks was called with both fallback models
        mock_primary.with_fallbacks.assert_called_once_with([mock_flash, mock_pro])
        assert result == mock_fallback_chain

    @patch("src.utils.llm_resilience.TIER_1_CONFIG")
    @patch("src.utils.llm_resilience.TIER_2_CONFIG")
    @patch("src.utils.llm_resilience.TIER_3_CONFIG")
    def test_emergency_fallback_when_primary_fails(self, mock_t3, mock_t2, mock_t1):
        """Verify emergency fallback to Gemini Flash when primary chain fails."""
        from src.utils.llm_resilience import get_resilient_llm

        # Make the primary LLM instantiation fail
        mock_t1.model_copy.return_value.get_chat_model.side_effect = Exception("Groq unavailable")
        mock_emergency = MagicMock()
        mock_t2.model_copy.return_value.get_chat_model.return_value = mock_emergency

        result = get_resilient_llm(task="fallback_test")

        assert result == mock_emergency

    @patch("src.utils.llm_resilience.TIER_1_CONFIG")
    @patch("src.utils.llm_resilience.TIER_2_CONFIG")
    @patch("src.utils.llm_resilience.TIER_3_CONFIG")
    def test_custom_temperature_propagated(self, mock_t3, mock_t2, mock_t1):
        """Verify custom temperature is passed to all tiers."""
        from src.utils.llm_resilience import get_resilient_llm

        mock_primary = MagicMock()
        mock_flash = MagicMock()
        mock_pro = MagicMock()

        mock_t1.model_copy.return_value.get_chat_model.return_value = mock_primary
        mock_t2.model_copy.return_value.get_chat_model.return_value = mock_flash
        mock_t3.model_copy.return_value.get_chat_model.return_value = mock_pro
        mock_primary.with_fallbacks.return_value = MagicMock()

        get_resilient_llm(task="temp_test", temperature=0.7)

        # Each tier should have been copied with the custom temperature
        mock_t1.model_copy.assert_called_once()
        update_arg = mock_t1.model_copy.call_args[1]["update"]
        assert update_arg["temperature"] == 0.7

    @patch("src.utils.llm_resilience.TIER_1_CONFIG")
    @patch("src.utils.llm_resilience.TIER_2_CONFIG")
    @patch("src.utils.llm_resilience.TIER_3_CONFIG")
    def test_circuit_breaker_in_callbacks(self, mock_t3, mock_t2, mock_t1):
        """Verify TokenCircuitBreakerHandler is included in callbacks."""
        from src.utils.llm_resilience import get_resilient_llm
        from src.utils.token_circuit_breaker import TokenCircuitBreakerHandler

        mock_primary = MagicMock()
        mock_flash = MagicMock()
        mock_pro = MagicMock()

        mock_t1.model_copy.return_value.get_chat_model.return_value = mock_primary
        mock_t2.model_copy.return_value.get_chat_model.return_value = mock_flash
        mock_t3.model_copy.return_value.get_chat_model.return_value = mock_pro
        mock_primary.with_fallbacks.return_value = MagicMock()

        get_resilient_llm(task="cb_test", token_budget=10000)

        # Check that get_chat_model was called with callbacks containing our breaker
        call_kwargs = mock_t1.model_copy.return_value.get_chat_model.call_args[1]
        assert "callbacks" in call_kwargs
        breaker_found = any(
            isinstance(cb, TokenCircuitBreakerHandler) for cb in call_kwargs["callbacks"]
        )
        assert breaker_found, "TokenCircuitBreakerHandler not found in callbacks"


class TestMonitoringProvenance:
    """Tests for correlation ID extraction in monitoring callbacks."""

    def test_cid_extraction_bracket_format(self):
        """Verify [CID:xxx] pattern is extracted from tool output."""
        from src.utils.monitoring import _CID_PATTERN

        output = "Retrieved data [CID:log-W27-2026-07-05-morning-Hero] from vector search"
        matches = _CID_PATTERN.findall(output)
        cids = [m[0] or m[1] for m in matches if m[0] or m[1]]
        assert "log-W27-2026-07-05-morning-Hero" in cids

    def test_cid_extraction_key_value_format(self):
        """Verify correlation_id=xxx pattern is extracted from tool output."""
        from src.utils.monitoring import _CID_PATTERN

        output = "correlation_id=weekly-W27-2026-07-01-Hero found in metadata"
        matches = _CID_PATTERN.findall(output)
        cids = [m[0] or m[1] for m in matches if m[0] or m[1]]
        assert "weekly-W27-2026-07-01-Hero" in cids

    def test_no_cid_returns_empty(self):
        """Verify no false positives on output without correlation IDs."""
        from src.utils.monitoring import _CID_PATTERN

        output = "Generic tool output with no lineage data"
        matches = _CID_PATTERN.findall(output)
        cids = [m[0] or m[1] for m in matches if m[0] or m[1]]
        assert len(cids) == 0
