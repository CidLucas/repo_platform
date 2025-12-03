"""Google Sheets Client implementation"""
from typing import List, Any
from .models import SheetWriteResult, SheetReadResult
from ..base import BaseGoogleClient


class GoogleSheetsClient(BaseGoogleClient):
    """Google Sheets API client."""

    def _build_service(self):
        try:
            from googleapiclient.discovery import build  # type: ignore
        except ImportError:
            raise ImportError("google-api-python-client not installed; install it to use Sheets client")

        creds = self._get_credentials()
        return build("sheets", "v4", credentials=creds, cache_discovery=False)

    async def create_spreadsheet(self, title: str) -> dict:
        """Create a new spreadsheet and return its ID and URL."""
        service = self._build_service()
        spreadsheet = {"properties": {"title": title}}
        result = service.spreadsheets().create(body=spreadsheet, fields="spreadsheetId,spreadsheetUrl").execute()
        return {
            "spreadsheet_id": result.get("spreadsheetId"),
            "spreadsheet_url": result.get("spreadsheetUrl"),
        }

    async def append_values(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: List[List[Any]],
        value_input_option: str = "USER_ENTERED",
    ) -> SheetWriteResult:
        """Append values to a spreadsheet."""
        service = self._build_service()
        body = {"values": values}
        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption=value_input_option,
            body=body,
        ).execute()

        updates = result.get("updates", {})
        return SheetWriteResult(
            spreadsheet_id=spreadsheet_id,
            updated_range=updates.get("updatedRange"),
            updated_rows=updates.get("updatedRows"),
            updated_columns=updates.get("updatedColumns"),
            updated_cells=updates.get("updatedCells"),
        )

    async def read_values(self, spreadsheet_id: str, range_name: str) -> SheetReadResult:
        """Read values from a spreadsheet."""
        service = self._build_service()
        result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
        return SheetReadResult(
            spreadsheet_id=spreadsheet_id,
            range=result.get("range"),
            values=result.get("values", []),
            major_dimension=result.get("majorDimension", "ROWS"),
        )
