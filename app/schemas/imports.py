"""Pydantic schemas for CSV and Excel Import endpoints."""
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class ImportValidationError(BaseModel):
    """Detailed validation error for a specific row in an imported file."""
    row_number: int = Field(description="1-based row number in the file (excluding header)")
    field: str = Field(description="Column or field name where the error occurred")
    error: str = Field(description="Descriptive explanation of the validation error")
    raw_value: Optional[Any] = Field(default=None, description="The raw offending value from the file")


class ImportSummaryResponse(BaseModel):
    """Complete summary of the CSV or Excel import operation."""
    entity: str = Field(description="Imported entity type: 'members', 'memberships', or 'payments'")
    filename: str = Field(description="Original filename uploaded")
    total_rows_processed: int = Field(description="Total data rows read from the file")
    successful_imports: int = Field(description="Number of records successfully created")
    failed_records: int = Field(description="Number of rows that failed validation or constraints")
    duplicate_records: int = Field(description="Number of duplicate rows skipped or rejected")
    dry_run: bool = Field(description="True if validation-only preview without committing changes")
    errors: List[ImportValidationError] = Field(
        default_factory=list,
        description="Detailed list of row-level errors and reasons"
    )
    imported_ids: List[str] = Field(
        default_factory=list,
        description="List of UUID strings for successfully created entities"
    )

