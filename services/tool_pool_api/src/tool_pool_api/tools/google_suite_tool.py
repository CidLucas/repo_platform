from datetime import datetime
from typing import Any
from uuid import UUID

from mcp.server import Server

from vizu_context_service import ContextService
from vizu_google_suite_client import (
    GoogleCalendarClient,
    GoogleGmailClient,
    GoogleSheetsClient,
)

# Create a local Server instance so the decorator used in the snippet is available
mcp = Server("google-suite")


class GoogleSuiteTool:
    def __init__(self, context_service: ContextService):
        self.context_service = context_service

    async def _get_user_tokens(self, cliente_vizu_id: UUID) -> dict:
        """Recupera tokens OAuth do vizu_context_service"""
        integration = await self.context_service.get_integration_tokens(
            cliente_vizu_id=cliente_vizu_id, provider="google"
        )
        if not integration or not getattr(integration, "is_valid", lambda: True)():
            raise ValueError("Google integration not configured or expired")
        # Expecting context service to return an object with get_decrypted_tokens()
        return await getattr(integration, "get_decrypted_tokens", lambda: integration)()

    @mcp.tool()
    async def write_to_sheet(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: list[list[Any]],
        cliente_vizu_id: UUID,  # Injetado pelo auth middleware
    ) -> dict:
        """Escreve dados em uma planilha Google Sheets"""
        tokens = await self._get_user_tokens(cliente_vizu_id)
        client = GoogleSheetsClient(access_token=tokens["access_token"])
        result = await client.append_values(spreadsheet_id, range_name, values)
        return {"status": "success", "updated_cells": result.updated_cells}

    @mcp.tool()
    async def read_emails(
        self, query: str, max_results: int = 10, cliente_vizu_id: UUID | None = None
    ) -> list[dict]:
        """Busca e lê emails do Gmail"""
        if cliente_vizu_id is None:
            raise ValueError("cliente_vizu_id is required")
        tokens = await self._get_user_tokens(cliente_vizu_id)
        client = GoogleGmailClient(access_token=tokens["access_token"])
        emails = await client.search_messages(query, max_results)
        return [email.to_dict() for email in emails]

    @mcp.tool()
    async def query_calendar(
        self,
        time_min: datetime,
        time_max: datetime,
        calendar_id: str = "primary",
        cliente_vizu_id: UUID | None = None,
    ) -> list[dict]:
        """Consulta eventos do Google Calendar"""
        if cliente_vizu_id is None:
            raise ValueError("cliente_vizu_id is required")
        tokens = await self._get_user_tokens(cliente_vizu_id)
        client = GoogleCalendarClient(access_token=tokens["access_token"])
        events = await client.list_events(calendar_id, time_min, time_max)
        return [event.to_dict() for event in events]
