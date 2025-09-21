"""Tests for logging configuration implementation."""

import logging
import sys
from unittest.mock import MagicMock, patch

import pytest

from ml_agents_v2.config.application_config import ApplicationConfig
from ml_agents_v2.infrastructure.logging_config import configure_logging, get_logger


class TestConfigureLogging:
    """Test configure_logging function."""

    @pytest.fixture
    def debug_config(self):
        """Create application config for debug mode."""
        config = MagicMock(spec=ApplicationConfig)
        config.log_level = "DEBUG"
        config.debug_mode = True
        return config

    @pytest.fixture
    def production_config(self):
        """Create application config for production mode."""
        config = MagicMock(spec=ApplicationConfig)
        config.log_level = "INFO"
        config.debug_mode = False
        return config

    @patch("logging.basicConfig")
    @patch("structlog.configure")
    def test_configure_logging_debug_mode(
        self, mock_structlog_configure, mock_logging_config, debug_config
    ):
        """Test logging configuration in debug mode."""
        configure_logging(debug_config)

        # Verify standard library logging configuration
        mock_logging_config.assert_called_once_with(
            level=logging.DEBUG,
            format="%(message)s",
            stream=sys.stdout,
        )

        # Verify structlog configuration was called
        mock_structlog_configure.assert_called_once()

        # Extract the call arguments
        call_args = mock_structlog_configure.call_args
        assert "processors" in call_args.kwargs
        assert "wrapper_class" in call_args.kwargs
        assert "logger_factory" in call_args.kwargs
        assert "cache_logger_on_first_use" in call_args.kwargs

        # Verify cache_logger_on_first_use is True
        assert call_args.kwargs["cache_logger_on_first_use"] is True

    @patch("logging.basicConfig")
    @patch("structlog.configure")
    def test_configure_logging_production_mode(
        self, mock_structlog_configure, mock_logging_config, production_config
    ):
        """Test logging configuration in production mode."""
        configure_logging(production_config)

        # Verify standard library logging configuration
        mock_logging_config.assert_called_once_with(
            level=logging.INFO,
            format="%(message)s",
            stream=sys.stdout,
        )

        # Verify structlog configuration was called
        mock_structlog_configure.assert_called_once()

    @patch("logging.basicConfig")
    @patch("structlog.configure")
    def test_configure_logging_different_log_levels(
        self, mock_structlog_configure, mock_logging_config
    ):
        """Test logging configuration with different log levels."""
        test_cases = [
            ("DEBUG", logging.DEBUG),
            ("INFO", logging.INFO),
            ("WARNING", logging.WARNING),
            ("ERROR", logging.ERROR),
            ("CRITICAL", logging.CRITICAL),
        ]

        for level_str, expected_level in test_cases:
            mock_logging_config.reset_mock()
            mock_structlog_configure.reset_mock()

            config = MagicMock(spec=ApplicationConfig)
            config.log_level = level_str
            config.debug_mode = False

            configure_logging(config)

            # Verify correct log level was set
            mock_logging_config.assert_called_once()
            call_args = mock_logging_config.call_args
            assert call_args.kwargs["level"] == expected_level

    @patch("logging.basicConfig")
    @patch("structlog.configure")
    @patch("structlog.dev.ConsoleRenderer")
    @patch("structlog.processors.JSONRenderer")
    def test_configure_logging_renderer_selection(
        self,
        mock_json_renderer,
        mock_console_renderer,
        mock_structlog_configure,
        mock_logging_config,
    ):
        """Test that correct renderer is selected based on debug mode."""
        # Test debug mode uses ConsoleRenderer
        debug_config = MagicMock(spec=ApplicationConfig)
        debug_config.log_level = "INFO"
        debug_config.debug_mode = True

        configure_logging(debug_config)
        mock_console_renderer.assert_called_once()

        # Reset mocks
        mock_console_renderer.reset_mock()
        mock_json_renderer.reset_mock()

        # Test production mode uses JSONRenderer
        prod_config = MagicMock(spec=ApplicationConfig)
        prod_config.log_level = "INFO"
        prod_config.debug_mode = False

        configure_logging(prod_config)
        mock_json_renderer.assert_called_once()

    @patch("logging.basicConfig")
    @patch("structlog.configure")
    def test_configure_logging_processors_order(
        self, mock_structlog_configure, mock_logging_config, debug_config
    ):
        """Test that processors are configured in correct order."""
        configure_logging(debug_config)

        # Get the processors list from the call
        call_args = mock_structlog_configure.call_args
        processors = call_args.kwargs["processors"]

        # Verify we have the expected number of processors
        assert len(processors) == 6

        # Verify processor types (order matters)
        processor_names = [
            proc.__name__ if hasattr(proc, "__name__") else str(type(proc))
            for proc in processors
        ]

        # Check that key processors are present
        assert any("merge_contextvars" in name for name in processor_names)
        assert any("add_log_level" in name for name in processor_names)
        assert any("TimeStamper" in name for name in processor_names)

    @patch("logging.basicConfig")
    @patch("structlog.configure")
    @patch("structlog.make_filtering_bound_logger")
    def test_configure_logging_wrapper_class(
        self,
        mock_make_filtering,
        mock_structlog_configure,
        mock_logging_config,
        production_config,
    ):
        """Test that wrapper class is properly configured."""
        mock_wrapper_class = MagicMock()
        mock_make_filtering.return_value = mock_wrapper_class

        configure_logging(production_config)

        # Verify filtering bound logger is created with correct log level
        mock_make_filtering.assert_called_once_with(logging.INFO)

        # Verify wrapper class is used in structlog configuration
        call_args = mock_structlog_configure.call_args
        assert call_args.kwargs["wrapper_class"] == mock_wrapper_class

    @patch("logging.basicConfig")
    @patch("structlog.configure")
    @patch("structlog.WriteLoggerFactory")
    def test_configure_logging_logger_factory(
        self,
        mock_logger_factory,
        mock_structlog_configure,
        mock_logging_config,
        debug_config,
    ):
        """Test that logger factory is properly configured."""
        mock_factory_instance = MagicMock()
        mock_logger_factory.return_value = mock_factory_instance

        configure_logging(debug_config)

        # Verify WriteLoggerFactory is instantiated
        mock_logger_factory.assert_called_once()

        # Verify logger factory is used in structlog configuration
        call_args = mock_structlog_configure.call_args
        assert call_args.kwargs["logger_factory"] == mock_factory_instance

    def test_configure_logging_case_insensitive_log_level(self):
        """Test that log level configuration is case insensitive."""
        with patch("logging.basicConfig") as mock_logging_config:
            with patch("structlog.configure"):
                # Test lowercase
                config = MagicMock(spec=ApplicationConfig)
                config.log_level = "debug"
                config.debug_mode = True

                configure_logging(config)

                call_args = mock_logging_config.call_args
                assert call_args.kwargs["level"] == logging.DEBUG

    @patch("logging.basicConfig")
    @patch("structlog.configure")
    def test_configure_logging_idempotent(
        self, mock_structlog_configure, mock_logging_config, debug_config
    ):
        """Test that calling configure_logging multiple times is safe."""
        # Call configure_logging twice
        configure_logging(debug_config)
        configure_logging(debug_config)

        # Both calls should succeed (no exceptions)
        assert mock_logging_config.call_count == 2
        assert mock_structlog_configure.call_count == 2


class TestGetLogger:
    """Test get_logger function."""

    @patch("structlog.get_logger")
    def test_get_logger_basic(self, mock_structlog_get_logger):
        """Test basic get_logger functionality."""
        mock_logger = MagicMock()
        mock_structlog_get_logger.return_value = mock_logger

        result = get_logger("test_module")

        mock_structlog_get_logger.assert_called_once_with("test_module")
        assert result == mock_logger

    @patch("structlog.get_logger")
    def test_get_logger_with_module_name(self, mock_structlog_get_logger):
        """Test get_logger with __name__ pattern."""
        mock_logger = MagicMock()
        mock_structlog_get_logger.return_value = mock_logger

        module_name = "ml_agents_v2.infrastructure.test_module"
        result = get_logger(module_name)

        mock_structlog_get_logger.assert_called_once_with(module_name)
        assert result == mock_logger

    @patch("structlog.get_logger")
    def test_get_logger_multiple_calls(self, mock_structlog_get_logger):
        """Test multiple get_logger calls with different names."""
        mock_logger1 = MagicMock()
        mock_logger2 = MagicMock()
        mock_structlog_get_logger.side_effect = [mock_logger1, mock_logger2]

        result1 = get_logger("module1")
        result2 = get_logger("module2")

        assert mock_structlog_get_logger.call_count == 2
        assert result1 == mock_logger1
        assert result2 == mock_logger2

    @patch("structlog.get_logger")
    def test_get_logger_returns_bound_logger(self, mock_structlog_get_logger):
        """Test that get_logger returns a bound logger instance."""
        # Create a mock that has the expected bound logger interface
        mock_logger = MagicMock()
        mock_logger.info = MagicMock()
        mock_logger.error = MagicMock()
        mock_logger.debug = MagicMock()
        mock_logger.warning = MagicMock()
        mock_logger.critical = MagicMock()

        mock_structlog_get_logger.return_value = mock_logger

        result = get_logger("test")

        # Verify the logger has the expected interface
        assert hasattr(result, "info")
        assert hasattr(result, "error")
        assert hasattr(result, "debug")
        assert hasattr(result, "warning")
        assert hasattr(result, "critical")

    def test_get_logger_integration_with_configure_logging(self):
        """Test that get_logger works after configure_logging is called."""
        # This is an integration test that doesn't mock structlog
        config = MagicMock(spec=ApplicationConfig)
        config.log_level = "INFO"
        config.debug_mode = True

        # Configure logging first
        configure_logging(config)

        # Then get a logger
        logger = get_logger("test_integration")

        # Verify we get a logger instance
        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")


class TestLoggingIntegration:
    """Integration tests for logging configuration."""

    def test_end_to_end_debug_logging(self):
        """Test complete logging setup and usage in debug mode."""
        config = MagicMock(spec=ApplicationConfig)
        config.log_level = "DEBUG"
        config.debug_mode = True

        # Configure logging
        configure_logging(config)

        # Get a logger
        logger = get_logger("test_debug")

        # Verify logger can be used (should not raise exceptions)
        try:
            logger.info("Test message", extra_data="test")
            logger.debug("Debug message")
            logger.error("Error message", error="test error")
        except Exception as e:
            pytest.fail(f"Logging should not raise exceptions: {e}")

    def test_end_to_end_production_logging(self):
        """Test complete logging setup and usage in production mode."""
        config = MagicMock(spec=ApplicationConfig)
        config.log_level = "WARNING"
        config.debug_mode = False

        # Configure logging
        configure_logging(config)

        # Get a logger
        logger = get_logger("test_production")

        # Verify logger can be used (should not raise exceptions)
        try:
            logger.warning("Warning message", context="production")
            logger.error("Error in production", service="test")
            logger.critical("Critical issue", alert=True)
        except Exception as e:
            pytest.fail(f"Logging should not raise exceptions: {e}")
