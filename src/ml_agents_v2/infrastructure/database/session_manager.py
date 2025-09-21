"""Database session management for SQLAlchemy operations."""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Union

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ml_agents_v2.infrastructure.database.base import Base


class DatabaseSessionManager:
    """Manages SQLAlchemy database sessions with proper transaction handling.

    Provides context managers for database operations with automatic
    commit/rollback and resource cleanup.
    """

    def __init__(self, database_url: str, echo: bool = False):
        """Initialize session manager with database URL.

        Args:
            database_url: SQLAlchemy database connection URL
            echo: Whether to echo SQL statements for debugging
        """
        self.database_url = database_url
        self.engine = create_engine(database_url, echo=echo)
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
        )

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session with automatic transaction management.

        Yields:
            SQLAlchemy session with automatic commit/rollback

        Usage:
            with session_manager.get_session() as session:
                # Database operations here
                session.add(model_instance)
                # Automatically committed on success, rolled back on exception
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_tables(self) -> None:
        """Create all database tables defined in SQLAlchemy models.

        This method creates all tables defined in the Base metadata.
        Should be called during application initialization or migrations.
        """
        Base.metadata.create_all(bind=self.engine)

    def drop_tables(self) -> None:
        """Drop all database tables.

        WARNING: This will delete all data in the database.
        Should only be used for testing or clean deployments.
        """
        Base.metadata.drop_all(bind=self.engine)


# Global session manager instance (will be initialized by dependency injection)
_session_manager: Union[DatabaseSessionManager, None] = None


def get_session_manager() -> DatabaseSessionManager:
    """Get the global session manager instance.

    Returns:
        DatabaseSessionManager instance

    Raises:
        RuntimeError: If session manager has not been initialized
    """
    if _session_manager is None:
        raise RuntimeError(
            "DatabaseSessionManager not initialized. "
            "Call initialize_session_manager() first."
        )
    return _session_manager


def initialize_session_manager(database_url: str, echo: bool = False) -> None:
    """Initialize the global session manager.

    Args:
        database_url: SQLAlchemy database connection URL
        echo: Whether to echo SQL statements for debugging
    """
    global _session_manager
    _session_manager = DatabaseSessionManager(database_url, echo)
