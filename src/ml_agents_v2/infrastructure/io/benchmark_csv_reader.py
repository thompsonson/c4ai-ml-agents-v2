"""CSV reader for benchmark import functionality."""

import csv
import logging
from pathlib import Path
from typing import Any

from ml_agents_v2.core.domain.value_objects.question import Question


class BenchmarkCsvReader:
    """Infrastructure utility for reading benchmark CSV files.

    Handles conversion from CSV INPUT,OUTPUT format to domain Question objects.
    This is an infrastructure concern - handles file I/O and format conversion.
    """

    def __init__(self) -> None:
        """Initialize CSV reader."""
        self._logger = logging.getLogger(__name__)

    def read_questions_from_csv(self, file_path: str) -> list[Question]:
        """Read questions from CSV file with INPUT,OUTPUT columns.

        Args:
            file_path: Path to CSV file containing INPUT,OUTPUT columns

        Returns:
            List of Question domain objects

        Raises:
            FileNotFoundError: If CSV file doesn't exist
            ValueError: If CSV format is invalid or missing required columns
            IOError: If file cannot be read
        """
        csv_path = Path(file_path)

        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        if not csv_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        self._logger.info(f"Reading questions from CSV file: {file_path}")

        try:
            questions = []

            with open(csv_path, encoding="utf-8") as file:
                reader = csv.DictReader(file)

                # Validate required columns
                if not reader.fieldnames:
                    raise ValueError("CSV file appears to be empty or invalid")

                required_columns = {"INPUT", "OUTPUT"}
                available_columns = set(reader.fieldnames)

                if not required_columns.issubset(available_columns):
                    missing = required_columns - available_columns
                    raise ValueError(
                        f"CSV file missing required columns: {missing}. "
                        f"Found columns: {available_columns}"
                    )

                # Process each row
                for row_num, row in enumerate(reader, start=1):
                    try:
                        # Validate row data
                        input_text = row.get("INPUT", "").strip()
                        output_text = row.get("OUTPUT", "").strip()

                        if not input_text:
                            self._logger.warning(
                                f"Row {row_num}: Empty INPUT field, skipping"
                            )
                            continue

                        if not output_text:
                            self._logger.warning(
                                f"Row {row_num}: Empty OUTPUT field, skipping"
                            )
                            continue

                        # Create Question object with generated ID
                        question = Question(
                            id=str(row_num),  # Sequential ID based on CSV row
                            text=input_text,
                            expected_answer=output_text,
                            metadata=self._extract_metadata(row, row_num),
                        )

                        questions.append(question)

                    except Exception as e:
                        self._logger.error(f"Error processing row {row_num}: {e}")
                        # Continue processing other rows rather than failing completely
                        continue

            if not questions:
                raise ValueError("No valid questions found in CSV file")

            self._logger.info(
                f"Successfully read {len(questions)} questions from {file_path}"
            )

            return questions

        except OSError as e:
            self._logger.error(f"Failed to read CSV file {file_path}: {e}")
            raise OSError(f"Cannot read CSV file: {e}") from e

        except csv.Error as e:
            self._logger.error(f"CSV parsing error in {file_path}: {e}")
            raise ValueError(f"Invalid CSV format: {e}") from e

    def _extract_metadata(self, row: dict[str, Any], row_num: int) -> dict[str, Any]:
        """Extract metadata from CSV row beyond INPUT/OUTPUT columns.

        Args:
            row: CSV row data
            row_num: Row number for reference

        Returns:
            Metadata dictionary with any additional columns
        """
        metadata = {}

        # Add any additional columns as metadata
        for key, value in row.items():
            if key not in {"INPUT", "OUTPUT"} and value and value.strip():
                metadata[key.lower()] = value.strip()

        # Add row number for reference
        metadata["csv_row_number"] = row_num

        return metadata

    def validate_csv_format(self, file_path: str) -> tuple[bool, list[str]]:
        """Validate CSV file format without fully reading it.

        Args:
            file_path: Path to CSV file to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        try:
            csv_path = Path(file_path)

            if not csv_path.exists():
                errors.append(f"File does not exist: {file_path}")
                return False, errors

            if not csv_path.is_file():
                errors.append(f"Path is not a file: {file_path}")
                return False, errors

            # Check file size (basic sanity check)
            if csv_path.stat().st_size == 0:
                errors.append("File is empty")
                return False, errors

            # Check CSV structure
            with open(csv_path, encoding="utf-8") as file:
                reader = csv.DictReader(file)

                if not reader.fieldnames:
                    errors.append("CSV file has no headers")
                    return False, errors

                required_columns = {"INPUT", "OUTPUT"}
                available_columns = set(reader.fieldnames)

                if not required_columns.issubset(available_columns):
                    missing = required_columns - available_columns
                    errors.append(
                        f"Missing required columns: {missing}. "
                        f"Found: {available_columns}"
                    )
                    return False, errors

                # Check if there's at least one data row
                try:
                    first_row = next(reader)
                    if not any(first_row.values()):
                        errors.append("First data row appears to be empty")
                        return False, errors
                except StopIteration:
                    errors.append("CSV file has headers but no data rows")
                    return False, errors

        except Exception as e:
            errors.append(f"Error validating CSV file: {e}")
            return False, errors

        return True, errors
