"""Tests for Alembic migration setup."""

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text

from alembic import command


class TestAlembicSetup:
    """Test Alembic migration configuration and initial schema."""

    @pytest.fixture
    def temp_database_url(self, tmp_path):
        """Create temporary SQLite database for testing migrations."""
        db_path = tmp_path / "test_migration.db"
        return f"sqlite:///{db_path}"

    @pytest.fixture
    def alembic_config(self, temp_database_url):
        """Create Alembic configuration for testing."""
        # Get project root directory
        project_root = Path(__file__).parent.parent.parent.parent
        alembic_ini_path = project_root / "alembic.ini"

        if not alembic_ini_path.exists():
            pytest.skip("alembic.ini not found - Alembic not configured yet")

        config = Config(str(alembic_ini_path))
        config.set_main_option("sqlalchemy.url", temp_database_url)
        return config

    def test_alembic_ini_exists(self):
        """Test that alembic.ini configuration file exists."""
        project_root = Path(__file__).parent.parent.parent.parent
        alembic_ini_path = project_root / "alembic.ini"

        assert alembic_ini_path.exists(), "alembic.ini configuration file should exist"

    def test_migrations_directory_exists(self):
        """Test that migrations directory structure exists."""
        # Get the correct path to the migrations directory
        project_root = Path(__file__).parent.parent.parent.parent
        migrations_dir = (
            project_root
            / "src"
            / "ml_agents_v2"
            / "infrastructure"
            / "database"
            / "migrations"
        )

        assert migrations_dir.exists(), "Migrations directory should exist"
        assert (
            migrations_dir / "env.py"
        ).exists(), "env.py should exist in migrations directory"

    def test_initial_migration_creates_tables(self, alembic_config, temp_database_url):
        """Test that initial migration creates the expected database tables."""
        # Run migration to head
        command.upgrade(alembic_config, "head")

        # Connect to database and verify tables exist
        engine = create_engine(temp_database_url)
        with engine.connect() as conn:
            # Check that evaluations table exists
            result = conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='evaluations'"
                )
            )
            assert result.fetchone() is not None, "evaluations table should be created"

            # Check that preprocessed_benchmarks table exists
            result = conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='preprocessed_benchmarks'"
                )
            )
            assert (
                result.fetchone() is not None
            ), "preprocessed_benchmarks table should be created"

    def test_migration_creates_proper_indexes(self, alembic_config, temp_database_url):
        """Test that migration creates proper indexes for performance."""
        # Run migration to head
        command.upgrade(alembic_config, "head")

        # Connect to database and verify indexes exist
        engine = create_engine(temp_database_url)
        with engine.connect() as conn:
            # Check for status index on evaluations
            result = conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='evaluations'"
                )
            )
            indexes = [row[0] for row in result.fetchall()]

            # Should have index on status for filtering
            status_indexes = [idx for idx in indexes if "status" in idx.lower()]
            assert len(status_indexes) > 0, "Should have index on evaluation status"

    def test_migration_rollback_works(self, alembic_config, temp_database_url):
        """Test that migration rollback properly removes tables."""
        # Run migration to head
        command.upgrade(alembic_config, "head")

        # Verify tables exist
        engine = create_engine(temp_database_url)
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN ('evaluations', 'preprocessed_benchmarks')"
                )
            )
            assert result.fetchone()[0] == 2, "Both tables should exist after migration"

        # Rollback migration
        command.downgrade(alembic_config, "base")

        # Verify tables are removed
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN ('evaluations', 'preprocessed_benchmarks')"
                )
            )
            assert result.fetchone()[0] == 0, "Tables should be removed after rollback"

    def test_migration_is_idempotent(self, alembic_config):
        """Test that running migration multiple times is safe."""
        # Run migration twice
        command.upgrade(alembic_config, "head")
        command.upgrade(alembic_config, "head")  # Should not fail

        # Should still be at head revision
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory

        script = ScriptDirectory.from_config(alembic_config)
        engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))

        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current_rev = context.get_current_revision()
            head_rev = script.get_current_head()

            assert (
                current_rev == head_rev
            ), "Should be at head revision after multiple upgrades"
