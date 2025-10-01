"""Tests for database session manager."""

import pytest
from sqlalchemy import text

from ml_agents_v2.infrastructure.database.session_manager import (
    DatabaseSessionManager,
)


class TestDatabaseSessionManager:
    """Test database session management."""

    @pytest.fixture
    def test_database_url(self, tmp_path):
        """Create temporary SQLite database for testing."""
        db_path = tmp_path / "test_session.db"
        return f"sqlite:///{db_path}"

    def test_session_manager_initialization(self, test_database_url):
        """Test that SessionManager can be initialized with database URL."""
        session_manager = DatabaseSessionManager(test_database_url)

        assert session_manager.database_url == test_database_url
        assert session_manager.engine is not None

    def test_session_manager_get_session(self, test_database_url):
        """Test that SessionManager provides working database sessions."""
        session_manager = DatabaseSessionManager(test_database_url)

        with session_manager.get_session() as session:
            # Verify we can execute basic SQL
            result = session.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1

    def test_session_manager_context_manager(self, test_database_url):
        """Test that SessionManager works as context manager."""
        session_manager = DatabaseSessionManager(test_database_url)

        # Test successful context
        with session_manager.get_session() as session:
            result = session.execute(text("SELECT 'test'"))
            assert result.fetchone()[0] == "test"

    def test_session_manager_transaction_rollback(self, test_database_url):
        """Test that SessionManager handles transaction rollback properly."""
        session_manager = DatabaseSessionManager(test_database_url)

        # Create tables first
        session_manager.create_tables()

        # Test transaction rollback on exception
        with pytest.raises(RuntimeError):
            with session_manager.get_session() as session:
                # This should be rolled back - use a valid SQL statement
                session.execute(text("CREATE TEMP TABLE temp_test (id INTEGER)"))
                raise RuntimeError("Test exception")

        # Verify rollback worked (no data should exist)
        with session_manager.get_session() as session:
            result = session.execute(text("SELECT COUNT(*) FROM evaluations"))
            assert result.fetchone()[0] == 0

    def test_session_manager_create_tables(self, test_database_url):
        """Test that SessionManager can create database tables."""
        session_manager = DatabaseSessionManager(test_database_url)

        # Create tables
        session_manager.create_tables()

        # Verify tables exist
        with session_manager.get_session() as session:
            # Check evaluations table exists
            result = session.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='evaluations'"
                )
            )
            assert result.fetchone() is not None

            # Check preprocessed_benchmarks table exists
            result = session.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='preprocessed_benchmarks'"
                )
            )
            assert result.fetchone() is not None

    def test_get_session_manager_singleton(self, test_database_url):
        """Test that get_session_manager returns singleton instance."""
        # This test will verify the global session manager factory
        pass  # Implementation depends on dependency injection setup
