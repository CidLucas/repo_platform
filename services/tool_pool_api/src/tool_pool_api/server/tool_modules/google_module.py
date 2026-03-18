"""Google Suite Tools Module

Registers Google-related tools (Sheets, Gmail, Calendar, Docs) with the MCP registry.
"""

import logging
from datetime import datetime
from uuid import UUID

from fastmcp import Context, FastMCP

from tool_pool_api.server.dependencies import get_context_service
from tool_pool_api.server.tool_modules import register_module
from vizu_google_suite_client import (
    GoogleCalendarClient,
    GoogleDocsClient,
    GoogleGmailClient,
    GoogleSheetsClient,
)

logger = logging.getLogger(__name__)


# =============================================================================
# LÓGICA DE NEGÓCIO (Testável)
# =============================================================================


async def _get_google_tokens(cliente_id: str, account_email: str | None = None) -> dict:
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


async def _list_spreadsheets_logic(
    cliente_id: str,
    max_results: int = 20,
    account_email: str | None = None,
) -> list:
    """List user's recent Google Spreadsheets."""
    tokens = await _get_google_tokens(cliente_id, account_email)
    client = GoogleSheetsClient(access_token=tokens["access_token"])
    spreadsheets = await client.list_spreadsheets(max_results)
    return spreadsheets


async def _export_data_to_sheet_logic(
    spreadsheet_id: str,
    sheet_name: str,
    values: list[list],
    cliente_id: str,
    account_email: str | None = None,
) -> dict:
    """Export data to an existing Google Sheet."""
    tokens = await _get_google_tokens(cliente_id, account_email)
    client = GoogleSheetsClient(access_token=tokens["access_token"])

    # Get existing sheet names to validate
    sheet_names = await client.get_sheet_names(spreadsheet_id)

    # Use provided sheet name or default to first sheet
    target_sheet = sheet_name if sheet_name in sheet_names else sheet_names[0]
    range_name = f"{target_sheet}!A1"

    result = await client.append_values(spreadsheet_id, range_name, values)

    return {
        "status": "success",
        "spreadsheet_id": spreadsheet_id,
        "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
        "sheet_name": target_sheet,
        "rows_written": len(values),
        "updated_cells": result.updated_cells,
    }


async def _create_spreadsheet_with_data_logic(
    title: str,
    values: list[list],
    cliente_id: str,
    account_email: str | None = None,
) -> dict:
    """Create a new Google Spreadsheet and populate with data."""
    tokens = await _get_google_tokens(cliente_id, account_email)
    client = GoogleSheetsClient(access_token=tokens["access_token"])

    # Create new spreadsheet
    spreadsheet = await client.create_spreadsheet(title)
    spreadsheet_id = spreadsheet["spreadsheet_id"]

    # Write data to the new spreadsheet
    if values:
        await client.append_values(spreadsheet_id, "A1", values)

    return {
        "status": "success",
        "spreadsheet_id": spreadsheet_id,
        "spreadsheet_url": spreadsheet["spreadsheet_url"],
        "rows_written": len(values),
    }


# ── Google Docs business logic ──────────────────────────────────────────────


async def _create_document_logic(
    title: str,
    cliente_id: str,
    account_email: str | None = None,
) -> dict:
    """Create a new Google Doc."""
    tokens = await _get_google_tokens(cliente_id, account_email)
    client = GoogleDocsClient(access_token=tokens["access_token"])
    result = await client.create_document(title)
    result["account_used"] = tokens.get("account_email")
    return result


async def _read_document_logic(
    document_id: str,
    cliente_id: str,
    account_email: str | None = None,
) -> dict:
    """Read a Google Doc and return its text content."""
    tokens = await _get_google_tokens(cliente_id, account_email)
    client = GoogleDocsClient(access_token=tokens["access_token"])
    result = await client.read_document(document_id)
    return {
        "document_id": result.document_id,
        "title": result.title,
        "body_text": result.body_text,
        "revision_id": result.revision_id,
        "account_used": tokens.get("account_email"),
    }


async def _write_document_logic(
    document_id: str,
    text: str,
    cliente_id: str,
    mode: str = "append",
    old_text: str | None = None,
    account_email: str | None = None,
) -> dict:
    """Write to a Google Doc (append text or replace text)."""
    tokens = await _get_google_tokens(cliente_id, account_email)
    client = GoogleDocsClient(access_token=tokens["access_token"])

    if mode == "replace" and old_text:
        result = await client.replace_text(document_id, old_text, text)
    else:
        result = await client.append_text(document_id, text)

    return {
        "status": "success",
        "document_id": result.document_id,
        "title": result.title,
        "replies": result.replies,
        "account_used": tokens.get("account_email"),
    }


async def _list_documents_logic(
    cliente_id: str,
    max_results: int = 20,
    account_email: str | None = None,
) -> list:
    """List user's recent Google Docs."""
    tokens = await _get_google_tokens(cliente_id, account_email)
    client = GoogleDocsClient(access_token=tokens["access_token"])
    return await client.list_documents(max_results)


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

    # Tool 5: List User's Spreadsheets
    async def list_spreadsheets_wrapper(
        max_results: int = 20,
        ctx: Context = None,
        cliente_id: str | None = None,
        account_email: str | None = None,
    ) -> list:
        """
        List user's recent Google Spreadsheets.

        Returns a list of spreadsheets with their IDs, titles, and URLs.
        Use this to let users select an existing spreadsheet for export.

        Args:
            max_results: Maximum number of spreadsheets to return (default 20)
            cliente_id: ID do cliente (injected internally)
            account_email: Optional Google account to use
        """
        if not cliente_id:
            raise ValueError("cliente_id is required")
        return await _list_spreadsheets_logic(cliente_id, max_results, account_email)

    mcp.tool(
        name="list_spreadsheets",
        description=(
            "List user's recent Google Spreadsheets. "
            "Returns spreadsheet IDs, titles, and URLs. "
            "Use this to let users select where to export data."
        ),
    )(list_spreadsheets_wrapper)

    # Tool 6: Export Data to Existing Sheet
    async def export_to_sheet_wrapper(
        spreadsheet_id: str,
        values: list[list],
        sheet_name: str = "Sheet1",
        ctx: Context = None,
        cliente_id: str | None = None,
        account_email: str | None = None,
    ) -> dict:
        """
        Export data to an existing Google Spreadsheet.

        Args:
            spreadsheet_id: ID of the target spreadsheet
            values: Data as list of rows (each row is a list of values)
            sheet_name: Name of the sheet tab (default "Sheet1")
            cliente_id: ID do cliente (injected internally)
            account_email: Optional Google account to use
        """
        if not cliente_id:
            raise ValueError("cliente_id is required")
        return await _export_data_to_sheet_logic(
            spreadsheet_id, sheet_name, values, cliente_id, account_email
        )

    mcp.tool(
        name="export_to_sheet",
        description=(
            "Export data to an existing Google Spreadsheet. "
            "Use after list_spreadsheets to let user select destination. "
            "Appends data to the specified sheet."
        ),
    )(export_to_sheet_wrapper)

    # Tool 7: Create New Spreadsheet with Data
    async def create_spreadsheet_with_data_wrapper(
        title: str,
        values: list[list],
        ctx: Context = None,
        cliente_id: str | None = None,
        account_email: str | None = None,
    ) -> dict:
        """
        Create a new Google Spreadsheet and populate with data.

        Args:
            title: Title for the new spreadsheet
            values: Data as list of rows (each row is a list of values)
            cliente_id: ID do cliente (injected internally)
            account_email: Optional Google account to use
        """
        if not cliente_id:
            raise ValueError("cliente_id is required")
        return await _create_spreadsheet_with_data_logic(title, values, cliente_id, account_email)

    mcp.tool(
        name="create_spreadsheet_with_data",
        description=(
            "Create a new Google Spreadsheet and populate with data. "
            "Use when user wants to create a fresh spreadsheet for export. "
            "Returns the new spreadsheet URL."
        ),
    )(create_spreadsheet_with_data_wrapper)

    # ── Google Docs Tools ───────────────────────────────────────────────

    # Tool 8: Create Google Doc
    async def google_docs_create_wrapper(
        title: str,
        ctx: Context = None,
        cliente_id: str | None = None,
        account_email: str | None = None,
    ) -> dict:
        """
        Create a new Google Docs document.

        Args:
            title: Title for the new document
            cliente_id: ID do cliente (injected internally)
            account_email: Optional Google account to use
        """
        if not cliente_id:
            raise ValueError("cliente_id is required")
        return await _create_document_logic(title, cliente_id, account_email)

    mcp.tool(
        name="google_docs_create",
        description=(
            """**Purpose:** Create a new Google Docs document.

**When to use this tool:**
- User asks to create a new document
- User wants to draft a report, letter, or document
- Generating content that should live in Google Docs

**Input format:**
- title: (string) Title for the new document
- account_email: (optional string) Specific Google account to use

**Examples:**
- "create a new Google Doc called Monthly Report"
- "make a document for meeting notes"
- "start a new draft in Google Docs"""
        ),
    )(google_docs_create_wrapper)

    # Tool 9: Read Google Doc
    async def google_docs_read_wrapper(
        document_id: str,
        ctx: Context = None,
        cliente_id: str | None = None,
        account_email: str | None = None,
    ) -> dict:
        """
        Read the content of a Google Docs document.

        Args:
            document_id: The ID of the document (from the URL)
            cliente_id: ID do cliente (injected internally)
            account_email: Optional Google account to use
        """
        if not cliente_id:
            raise ValueError("cliente_id is required")
        return await _read_document_logic(document_id, cliente_id, account_email)

    mcp.tool(
        name="google_docs_read",
        description=(
            """**Purpose:** Read the content of a Google Docs document.

**When to use this tool:**
- User asks to read or review a document
- User wants to see the contents of a Google Doc
- Fetching document content for analysis or summarization

**Input format:**
- document_id: (string) The document ID from the URL
- account_email: (optional string) Specific Google account to use

**Examples:**
- "read my Google Doc with ID abc123"
- "what's in this document?"
- "show me the contents of that Google Doc"""
        ),
    )(google_docs_read_wrapper)

    # Tool 10: Write to Google Doc
    async def google_docs_write_wrapper(
        document_id: str,
        text: str,
        mode: str = "append",
        old_text: str | None = None,
        ctx: Context = None,
        cliente_id: str | None = None,
        account_email: str | None = None,
    ) -> dict:
        """
        Write content to a Google Docs document.

        Args:
            document_id: The ID of the document (from the URL)
            text: The text to write (append) or the replacement text (replace mode)
            mode: "append" to add text at end, "replace" to find-and-replace
            old_text: Text to find and replace (required when mode is "replace")
            cliente_id: ID do cliente (injected internally)
            account_email: Optional Google account to use
        """
        if not cliente_id:
            raise ValueError("cliente_id is required")
        return await _write_document_logic(
            document_id, text, cliente_id, mode, old_text, account_email
        )

    mcp.tool(
        name="google_docs_write",
        description=(
            """**Purpose:** Write content to a Google Docs document.

**When to use this tool:**
- User asks to add text to an existing document
- User wants to append content (e.g., meeting notes, report sections)
- User wants to find and replace text in a document

**Input format:**
- document_id: (string) The document ID from the URL
- text: (string) Text to append or replacement text
- mode: (string) "append" (default) or "replace"
- old_text: (string, required for replace) Text to find and replace
- account_email: (optional string) Specific Google account to use

**Examples:**
- "add this paragraph to my document"
- "append the meeting notes to the Google Doc"
- "replace 'draft' with 'final' in the document"""
        ),
    )(google_docs_write_wrapper)

    # Tool 11: List Google Docs
    async def google_docs_list_wrapper(
        max_results: int = 20,
        ctx: Context = None,
        cliente_id: str | None = None,
        account_email: str | None = None,
    ) -> list:
        """
        List user's recent Google Docs documents.

        Returns a list of documents with their IDs, titles, and URLs.
        Use this to let users select a document to read or edit.

        Args:
            max_results: Maximum number of documents to return (default 20)
            cliente_id: ID do cliente (injected internally)
            account_email: Optional Google account to use
        """
        if not cliente_id:
            raise ValueError("cliente_id is required")
        return await _list_documents_logic(cliente_id, max_results, account_email)

    mcp.tool(
        name="google_docs_list",
        description=(
            """**Purpose:** List user's recent Google Docs documents.

**When to use this tool:**
- User asks to see their documents
- Before reading/writing, to let user pick a document
- User wants to find a specific document

**Input format:**
- max_results: (optional integer) Number of documents to return (default 20)
- account_email: (optional string) Specific Google account to use

**Examples:**
- "show me my recent Google Docs"
- "list my documents"
- "what documents do I have?"""
        ),
    )(google_docs_list_wrapper)

    logger.info(
        "[Google Module] Tools registered: write_to_sheet, read_emails, query_calendar, "
        "list_google_accounts, list_spreadsheets, export_to_sheet, create_spreadsheet_with_data, "
        "google_docs_create, google_docs_read, google_docs_write, google_docs_list"
    )
    return [
        "write_to_sheet",
        "read_emails",
        "query_calendar",
        "list_google_accounts",
        "list_spreadsheets",
        "export_to_sheet",
        "create_spreadsheet_with_data",
        "google_docs_create",
        "google_docs_read",
        "google_docs_write",
        "google_docs_list",
    ]
