"""Google Sheets Client implementation"""
from typing import Any

from ..base import BaseGoogleClient
from .models import SheetReadResult, SheetWriteResult


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
        values: list[list[Any]],
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

    async def list_spreadsheets(self, max_results: int = 20) -> list[dict]:
        """
        List user's recent spreadsheets from Google Drive.

        Args:
            max_results: Maximum number of spreadsheets to return

        Returns:
            List of dicts with spreadsheet_id, title, and url
        """
        try:
            from googleapiclient.discovery import build  # type: ignore
        except ImportError:
            raise ImportError("google-api-python-client not installed")

        creds = self._get_credentials()
        drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)

        # Query for spreadsheets only, ordered by most recent
        query = "mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
        results = drive_service.files().list(
            q=query,
            pageSize=max_results,
            fields="files(id, name, webViewLink, modifiedTime)",
            orderBy="modifiedTime desc",
        ).execute()

        files = results.get("files", [])
        return [
            {
                "spreadsheet_id": f["id"],
                "title": f["name"],
                "url": f.get("webViewLink", f"https://docs.google.com/spreadsheets/d/{f['id']}"),
                "modified_time": f.get("modifiedTime"),
            }
            for f in files
        ]

    async def get_sheet_names(self, spreadsheet_id: str) -> list[str]:
        """
        Get list of sheet names in a spreadsheet.

        Args:
            spreadsheet_id: The spreadsheet ID

        Returns:
            List of sheet names
        """
        service = self._build_service()
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = spreadsheet.get("sheets", [])
        return [sheet["properties"]["title"] for sheet in sheets]
