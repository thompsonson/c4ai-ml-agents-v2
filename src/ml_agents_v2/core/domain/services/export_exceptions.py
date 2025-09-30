"""Export service exceptions."""

from __future__ import annotations


class ExportError(Exception):
    """Base exception for export operations."""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        """Initialize export error.

        Args:
            message: Error description
            cause: Optional underlying exception
        """
        super().__init__(message)
        self.cause = cause


class InvalidExportDataError(ExportError):
    """Exception raised when export data is invalid or empty."""

    def __init__(self, data_issue: str) -> None:
        """Initialize invalid export data error.

        Args:
            data_issue: Description of the data problem
        """
        super().__init__(f"Invalid export data: {data_issue}")
        self.data_issue = data_issue


class ExportFormatError(ExportError):
    """Exception raised when export format is unsupported or invalid."""

    def __init__(self, format_name: str, supported_formats: list[str]) -> None:
        """Initialize export format error.

        Args:
            format_name: The unsupported format requested
            supported_formats: List of supported format names
        """
        super().__init__(
            f"Unsupported export format '{format_name}'. "
            f"Supported formats: {', '.join(supported_formats)}"
        )
        self.format_name = format_name
        self.supported_formats = supported_formats


class ExportFileError(ExportError):
    """Exception raised when file operations during export fail."""

    def __init__(self, file_path: str, operation: str, details: str) -> None:
        """Initialize export file error.

        Args:
            file_path: Path to the file that caused the error
            operation: The file operation that failed (e.g., 'write', 'create')
            details: Detailed error information
        """
        super().__init__(f"Failed to {operation} file '{file_path}': {details}")
        self.file_path = file_path
        self.operation = operation
        self.details = details
