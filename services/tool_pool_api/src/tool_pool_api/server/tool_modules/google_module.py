"""Google Suite Tools Module

Registers Google-related tools (Sheets, Gmail, Calendar) with the MCP registry.
"""

import logging
from datetime import datetime
from uuid import UUID

from fastmcp import Context, FastMCP

from tool_pool_api.server.dependencies import get_context_service
from tool_pool_api.server.tool_modules import register_module
from vizu_google_suite_client import (
    GoogleCalendarClient,
    GoogleGmailClient,
    GoogleSheetsClient,
)

logger = logging.getLogger(__name__)


# =============================================================================
# LÓGICA DE NEGÓCIO (Testável)
# =============================================================================


async def _get_google_tokens(
    cliente_id: str, account_email: str | None = None
) -> dict:
    """Helper to retrieve and validate Google tokens for a cliente.

    Args:
        cliente_id: The cliente UUID as string
        account_email: Optional specific account email. If None, uses default account.

    Returns:
        Dict with decrypted tokens including access_token, refresh_token, account_email, etc.

    Raises:
        ValueError: If no valid token found or integration not configured.
    """
    ctx_service = get_context_service()
    cliente_uuid = UUID(cliente_id)
    logger.info(
        f"[Google] Getting tokens for cliente: {cliente_uuid}, account: {account_email or 'default'}"
    )

    # auto_refresh=True will automatically refresh expired tokens
    token_wrapper = await ctx_service.get_integration_tokens(
        cliente_uuid,
        "google",
        auto_refresh=True,
        account_email=account_email,
    )

    if not token_wrapper:
        logger.error(f"[Google] No token_wrapper returned for cliente: {cliente_uuid}")
        raise ValueError(
            "Google integration not configured or expired. Please reconnect your Google account."
        )

    logger.info(f"[Google] token_wrapper found, is_valid={token_wrapper.is_valid()}")
    if not token_wrapper.is_valid():
        logger.error(f"[Google] Token is expired for cliente: {cliente_uuid}")
        raise ValueError(
            "Google integration not configured or expired. Please reconnect your Google account."
        )

    return token_wrapper.get_decrypted_tokens()


async def _write_to_sheet_logic(
    spreadsheet_id: str,
    range_name: str,
    values: list,
    cliente_id: str,
    account_email: str | None = None,
) -> dict:
    """Write data to a Google Sheet."""
    tokens = await _get_google_tokens(cliente_id, account_email)
    client = GoogleSheetsClient(access_token=tokens["access_token"])
    result = await client.append_values(spreadsheet_id, range_name, values)
    return {
        "status": "success",
        "updated_cells": result.updated_cells,
        "account_used": tokens.get("account_email"),
    }


async def _read_emails_logic(
    query: str,
    max_results: int,
    cliente_id: str,
    account_email: str | None = None,
) -> list:
    """Search and read Gmail messages."""
    tokens = await _get_google_tokens(cliente_id, account_email)
    client = GoogleGmailClient(access_token=tokens["access_token"])
    emails = await client.search_messages(query, max_results)
    return [e.to_dict() for e in emails]


async def _query_calendar_logic(
    time_min: str,
    time_max: str,
    calendar_id: str,
    cliente_id: str,
    account_email: str | None = None,
) -> list:
    """Query Google Calendar events."""
    tokens = await _get_google_tokens(cliente_id, account_email)
    client = GoogleCalendarClient(access_token=tokens["access_token"])

    # Parse ISO strings to datetime
    time_min_dt = datetime.fromisoformat(time_min.replace("Z", "+00:00"))
    time_max_dt = datetime.fromisoformat(time_max.replace("Z", "+00:00"))

    events = await client.list_events(calendar_id, time_min_dt, time_max_dt)
    return [ev.to_dict() for ev in events]


async def _list_google_accounts_logic(cliente_id: str) -> list:
    """List all connected Google accounts for a cliente."""
    ctx_service = get_context_service()
    cliente_uuid = UUID(cliente_id)
    accounts = await ctx_service.list_integration_accounts(cliente_uuid, "google")
    return accounts


# =============================================================================
# REGISTRO DO MÓDULO
# =============================================================================


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Register google suite tools."""

    # Tool 1: Write to Google Sheets
    async def write_to_sheet_wrapper(
        spreadsheet_id: str,
        range_name: str,
        values: list,
        ctx: Context,
        cliente_id: str | None = None,
        account_email: str | None = None,
    ) -> dict:
        """
        Write rows to a Google Sheets spreadsheet.

        Args:
            spreadsheet_id: The ID of the spreadsheet (from the URL)
            range_name: The A1 notation range (e.g., "Sheet1!A1:C10")
            values: List of rows to append, each row is a list of values
            cliente_id: ID do cliente (injected internally)
            account_email: Optional Google account email to use (uses default if not specified)
        """
        if not cliente_id:
            raise ValueError("cliente_id is required")
        return await _write_to_sheet_logic(
            spreadsheet_id, range_name, values, cliente_id, account_email
        )

    # Tool 2: Read Gmail Emails
    async def read_emails_wrapper(
        query: str,
        max_results: int = 10,
        ctx: Context = None,
        cliente_id: str | None = None,
        account_email: str | None = None,
    ) -> list:
        """
        Search and read Gmail messages.

        Args:
            query: Gmail search query (e.g., "from:user@example.com" or "is:unread")
            max_results: Maximum number of emails to return (default 10)
            cliente_id: ID do cliente (injected internally)
            account_email: Optional Google account email to use (uses default if not specified)
        """
        if not cliente_id:
            raise ValueError("cliente_id is required")
        return await _read_emails_logic(query, max_results, cliente_id, account_email)

    # Tool 3: Query Google Calendar
    async def query_calendar_wrapper(
        time_min: str,
        time_max: str,
        calendar_id: str = "primary",
        ctx: Context = None,
        cliente_id: str | None = None,
        account_email: str | None = None,
    ) -> list:
        """
        Query Google Calendar events within a time range.

        Args:
            time_min: Start time in ISO 8601 format (e.g., "2024-01-01T00:00:00Z")
            time_max: End time in ISO 8601 format (e.g., "2024-01-31T23:59:59Z")
            calendar_id: Calendar ID (default "primary" for main calendar)
            cliente_id: ID do cliente (injected internally)
            account_email: Optional Google account email to use (uses default if not specified)
        """
        if not cliente_id:
            raise ValueError("cliente_id is required")
        return await _query_calendar_logic(
            time_min, time_max, calendar_id, cliente_id, account_email
        )

    # Tool 4: List Google Accounts
    async def list_google_accounts_wrapper(
        ctx: Context = None,
        cliente_id: str | None = None,
    ) -> list:
        """
        List all connected Google accounts.

        Returns a list of connected Google accounts with their emails and status.
        Use this to see which accounts are available before using other Google tools.

        Args:
            cliente_id: ID do cliente (injected internally)
        """
        if not cliente_id:
            raise ValueError("cliente_id is required")
        return await _list_google_accounts_logic(cliente_id)

    # Register tools - the ctx and cliente_id params will be hidden from schema by FastMCP
    mcp.tool(
        name="write_to_sheet",
        description=(
            """**Purpose:** Write data to a Google Sheets spreadsheet.

**When to use this tool:**
- User wants to save data to a spreadsheet
- User asks to "add this to a Google Sheet"
- Recording data, logs, or information in tabular format
- Exporting conversation data or results

**Input format:**
- spreadsheet_id: (string) The ID from the spreadsheet URL
- range_name: (string) A1 notation range (e.g., "Sheet1!A1")
- values: (list of rows) Each row is a list of cell values
- account_email: (optional string) Specific Google account to use

**Examples:**
- "save these customer names to my spreadsheet"
- "add this data to row 5 of Sheet1"
- "append these results to my Google Sheet"""
        ),
    )(write_to_sheet_wrapper)

    mcp.tool(
        name="read_emails",
        description=(
            """**Purpose:** Search and read Gmail messages.

**When to use this tool:**
- User asks to check their email
- User wants to search for specific emails
- User needs information from recent correspondence
- Finding emails from specific senders or with specific content

**Input format:**
- query: (string) Gmail search query (e.g., "from:example.com", "is:unread")
- max_results: (optional integer) Number of emails to return (default 10)
- account_email: (optional string) Specific Google account to use

**Examples:**
- "check my unread emails from yesterday"
- "find emails from John about the project"
- "search for emails with 'invoice' in subject"
- "what's in my inbox right now?"""
        ),
    )(read_emails_wrapper)

    mcp.tool(
        name="query_calendar",
        description=(
           """ **Purpose:** Query Google Calendar events within a time range.

**When to use this tool:**
- User asks about their schedule or appointments
- User wants to check availability
- User needs to see upcoming meetings
- Scheduling coordination or planning

**Input format:**
- time_min: (string) ISO 8601 start time (e.g., "2024-01-01T00:00:00Z")
- time_max: (string) ISO 8601 end time
- calendar_id: (optional string) Calendar ID (default "primary")
- account_email: (optional string) Specific Google account to use

**Examples:**
- "what meetings do I have today?"
- "check my schedule for next week"
- "what's on my calendar tomorrow?"
- "show my appointments between 9am and 5pm"""
        ),
    )(query_calendar_wrapper)

    mcp.tool(
        name="list_google_accounts",
        description=(
            "List all connected Google accounts. "
            "Returns account emails, names, and which one is the default. "
            "Use this to see available accounts before using other Google tools."
        ),
    )(list_google_accounts_wrapper)

    logger.info(
        "[Google Module] Tools registered: write_to_sheet, read_emails, query_calendar, list_google_accounts"
    )
    return ["write_to_sheet", "read_emails", "query_calendar", "list_google_accounts"]
