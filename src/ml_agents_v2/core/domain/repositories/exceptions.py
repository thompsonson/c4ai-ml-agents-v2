"""Repository-specific exceptions."""

from __future__ import annotations


class RepositoryError(Exception):
    """Base exception for repository operations."""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        """Initialize repository error.

        Args:
            message: Error description
            cause: Optional underlying exception
        """
        super().__init__(message)
        self.cause = cause


class EntityNotFoundError(RepositoryError):
    """Exception raised when an entity is not found in the repository."""

    def __init__(self, entity_type: str, entity_id: str) -> None:
        """Initialize entity not found error.

        Args:
            entity_type: Type of entity that was not found
            entity_id: ID of the entity that was not found
        """
        super().__init__(f"{entity_type} with ID '{entity_id}' not found")
        self.entity_type = entity_type
        self.entity_id = entity_id


class DuplicateEntityError(RepositoryError):
    """Exception raised when attempting to create an entity that already exists."""

    def __init__(self, entity_type: str, entity_id: str) -> None:
        """Initialize duplicate entity error.

        Args:
            entity_type: Type of entity that already exists
            entity_id: ID of the duplicate entity
        """
        super().__init__(f"{entity_type} with ID '{entity_id}' already exists")
        self.entity_type = entity_type
        self.entity_id = entity_id


class RepositoryConnectionError(RepositoryError):
    """Exception raised when repository connection fails."""

    def __init__(self, message: str = "Failed to connect to repository") -> None:
        """Initialize repository connection error.

        Args:
            message: Error description
        """
        super().__init__(message)


class RepositoryTransactionError(RepositoryError):
    """Exception raised when repository transaction fails."""

    def __init__(self, message: str = "Repository transaction failed") -> None:
        """Initialize repository transaction error.

        Args:
            message: Error description
        """
        super().__init__(message)
