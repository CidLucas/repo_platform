from pydantic import BaseModel
from typing import List, Any, Optional


class SheetWriteResult(BaseModel):
    spreadsheet_id: str
    updated_range: Optional[str]
    updated_rows: Optional[int]
    updated_columns: Optional[int]
    updated_cells: Optional[int]


class SheetReadResult(BaseModel):
    spreadsheet_id: str
    range: str
    values: List[List[Any]]
    major_dimension: str
from pydantic import BaseModel
from typing import List, Any, Optional


class SheetWriteResult(BaseModel):
    spreadsheet_id: str
    updated_range: Optional[str]
    updated_rows: Optional[int]
    updated_columns: Optional[int]
    updated_cells: Optional[int]


class SheetReadResult(BaseModel):
    spreadsheet_id: str
    range: str
    values: List[List[Any]]
    major_dimension: str
