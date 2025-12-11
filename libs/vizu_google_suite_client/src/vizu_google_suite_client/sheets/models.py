from typing import Any

from pydantic import BaseModel


class SheetWriteResult(BaseModel):
    spreadsheet_id: str
    updated_range: str | None
    updated_rows: int | None
    updated_columns: int | None
    updated_cells: int | None


class SheetReadResult(BaseModel):
    spreadsheet_id: str
    range: str
    values: list[list[Any]]
    major_dimension: str
from typing import Any

from pydantic import BaseModel


class SheetWriteResult(BaseModel):
    spreadsheet_id: str
    updated_range: str | None
    updated_rows: int | None
    updated_columns: int | None
    updated_cells: int | None


class SheetReadResult(BaseModel):
    spreadsheet_id: str
    range: str
    values: list[list[Any]]
    major_dimension: str
