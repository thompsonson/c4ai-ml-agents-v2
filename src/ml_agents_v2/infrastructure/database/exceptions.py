"""Database infrastructure exceptions."""


class SerializationError(Exception):
    """Raised when domain objects cannot be serialized for persistence.

    Provides structured context for debugging JSON serialization failures
    in the infrastructure layer when handling untrusted data from LLMs,
    user inputs, and external APIs.
    """

    def __init__(
        self,
        entity_type: str,
        entity_id: str,
        field_name: str,
        original_error: Exception,
    ):
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.field_name = field_name
        self.original_error = original_error

        super().__init__(
            f"Failed to serialize {field_name} for {entity_type} {entity_id}: {original_error}"
        )
