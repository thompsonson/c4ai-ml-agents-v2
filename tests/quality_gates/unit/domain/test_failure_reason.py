"""Tests for FailureReason value object."""

from datetime import datetime

from ml_agents_v2.core.domain.value_objects.failure_reason import FailureReason


class TestFailureReason:
    """Test suite for FailureReason value object."""

    def test_failure_reason_creation(self) -> None:
        """Test FailureReason can be created with all attributes."""
        occurred_at = datetime.now()
        failure = FailureReason(
            category="parsing_error",
            description="Failed to parse model response",
            technical_details="JSONDecodeError: Expecting ',' delimiter",
            occurred_at=occurred_at,
            recoverable=False,
        )

        assert failure.category == "parsing_error"
        assert failure.description == "Failed to parse model response"
        assert failure.technical_details == "JSONDecodeError: Expecting ',' delimiter"
        assert failure.occurred_at == occurred_at
        assert failure.recoverable is False

    def test_failure_reason_value_equality(self) -> None:
        """Test FailureReason equality based on values."""
        occurred_at = datetime.now()
        failure1 = FailureReason(
            category="token_limit_exceeded",
            description="Request too long",
            technical_details="Context length: 5000, max: 4096",
            occurred_at=occurred_at,
            recoverable=True,
        )
        failure2 = FailureReason(
            category="token_limit_exceeded",
            description="Request too long",
            technical_details="Context length: 5000, max: 4096",
            occurred_at=occurred_at,
            recoverable=True,
        )

        assert failure1 == failure2

    def test_failure_reason_value_inequality(self) -> None:
        """Test FailureReason inequality when values differ."""
        occurred_at = datetime.now()
        failure1 = FailureReason(
            category="parsing_error",
            description="Failed to parse",
            technical_details="Error details",
            occurred_at=occurred_at,
            recoverable=False,
        )
        failure2 = FailureReason(
            category="network_timeout",
            description="Failed to parse",
            technical_details="Error details",
            occurred_at=occurred_at,
            recoverable=False,
        )

        assert failure1 != failure2

    def test_failure_reason_validation_valid_categories(self) -> None:
        """Test FailureReason accepts all valid categories."""
        valid_categories = [
            "parsing_error",
            "token_limit_exceeded",
            "content_guardrail",
            "model_refusal",
            "network_timeout",
            "rate_limit_exceeded",
            "credit_limit_exceeded",
            "authentication_error",
            "unknown",
        ]

        for category in valid_categories:
            failure = FailureReason(
                category=category,
                description="Test failure",
                technical_details="Test details",
                occurred_at=datetime.now(),
                recoverable=False,
            )
            assert failure.category == category

    def test_failure_reason_validation_invalid_category(self) -> None:
        """Test FailureReason validation fails for invalid category."""
        try:
            FailureReason(
                category="invalid_category",
                description="Test failure",
                technical_details="Test details",
                occurred_at=datetime.now(),
                recoverable=False,
            )
            raise AssertionError("Expected ValueError for invalid category")
        except ValueError as e:
            assert "Invalid failure category" in str(e)

    def test_failure_reason_validation_empty_description(self) -> None:
        """Test FailureReason validation fails for empty description."""
        try:
            FailureReason(
                category="parsing_error",
                description="",
                technical_details="Test details",
                occurred_at=datetime.now(),
                recoverable=False,
            )
            raise AssertionError("Expected ValueError for empty description")
        except ValueError as e:
            assert "Description cannot be empty" in str(e)

    def test_failure_reason_validation_whitespace_description(self) -> None:
        """Test FailureReason validation fails for whitespace-only description."""
        try:
            FailureReason(
                category="parsing_error",
                description="   ",
                technical_details="Test details",
                occurred_at=datetime.now(),
                recoverable=False,
            )
            raise AssertionError("Expected ValueError for whitespace-only description")
        except ValueError as e:
            assert "Description cannot be empty" in str(e)

    def test_failure_reason_immutability(self) -> None:
        """Test FailureReason is immutable."""
        failure = FailureReason(
            category="parsing_error",
            description="Test failure",
            technical_details="Test details",
            occurred_at=datetime.now(),
            recoverable=False,
        )

        try:
            failure.category = "different_category"  # type: ignore
            raise AssertionError("Expected error when trying to modify category")
        except (AttributeError, ValueError):
            pass  # Expected - frozen dataclass should prevent modification

    def test_failure_reason_is_recoverable(self) -> None:
        """Test is_recoverable method returns correct value."""
        recoverable_failure = FailureReason(
            category="network_timeout",
            description="Request timeout",
            technical_details="Timeout after 30s",
            occurred_at=datetime.now(),
            recoverable=True,
        )
        non_recoverable_failure = FailureReason(
            category="authentication_error",
            description="Invalid API key",
            technical_details="401 Unauthorized",
            occurred_at=datetime.now(),
            recoverable=False,
        )

        assert recoverable_failure.is_recoverable() is True
        assert non_recoverable_failure.is_recoverable() is False

    def test_failure_reason_get_category_description(self) -> None:
        """Test get_category_description provides human-friendly descriptions."""
        failure = FailureReason(
            category="token_limit_exceeded",
            description="Request too long",
            technical_details="Context length exceeded",
            occurred_at=datetime.now(),
            recoverable=True,
        )

        description = failure.get_category_description()
        assert isinstance(description, str)
        assert len(description) > 0
        assert "token" in description.lower()

    def test_failure_reason_all_categories_have_descriptions(self) -> None:
        """Test all valid categories have meaningful descriptions."""
        valid_categories = [
            "parsing_error",
            "token_limit_exceeded",
            "content_guardrail",
            "model_refusal",
            "network_timeout",
            "rate_limit_exceeded",
            "credit_limit_exceeded",
            "authentication_error",
            "unknown",
        ]

        for category in valid_categories:
            failure = FailureReason(
                category=category,
                description="Test failure",
                technical_details="Test details",
                occurred_at=datetime.now(),
                recoverable=False,
            )
            description = failure.get_category_description()
            assert isinstance(description, str)
            assert len(description) > 10  # Meaningful description
