"""Unit tests for GoogleDocsClient.

Mocks the Google Docs API v1 and Drive API v3 to test
create, read, append, replace, and list operations.
"""

import pytest
from unittest.mock import MagicMock, patch

from vizu_google_suite_client.docs.client import GoogleDocsClient
from vizu_google_suite_client.docs.models import DocReadResult, DocWriteResult


@pytest.fixture
def client():
    return GoogleDocsClient(access_token="fake-access-token")


@pytest.fixture
def mock_docs_service():
    """Creates a mock Google Docs API service."""
    service = MagicMock()
    return service


@pytest.fixture
def mock_drive_service():
    """Creates a mock Google Drive API service."""
    service = MagicMock()
    return service


class TestCreateDocument:
    @pytest.mark.asyncio
    async def test_creates_document_and_returns_info(self, client, mock_docs_service):
        mock_docs_service.documents().create().execute.return_value = {
            "documentId": "doc-123",
            "title": "My New Doc",
        }

        with patch.object(client, "_build_service", return_value=mock_docs_service):
            result = await client.create_document("My New Doc")

        assert result["document_id"] == "doc-123"
        assert result["title"] == "My New Doc"
        assert "docs.google.com/document/d/doc-123" in result["document_url"]

    @pytest.mark.asyncio
    async def test_handles_missing_title_in_response(self, client, mock_docs_service):
        mock_docs_service.documents().create().execute.return_value = {
            "documentId": "doc-456",
        }

        with patch.object(client, "_build_service", return_value=mock_docs_service):
            result = await client.create_document("Requested Title")

        assert result["document_id"] == "doc-456"
        assert result["title"] == "Requested Title"


class TestReadDocument:
    @pytest.mark.asyncio
    async def test_reads_document_and_extracts_text(self, client, mock_docs_service):
        mock_docs_service.documents().get().execute.return_value = {
            "documentId": "doc-789",
            "title": "Test Doc",
            "revisionId": "rev-1",
            "body": {
                "content": [
                    {
                        "paragraph": {
                            "elements": [
                                {"textRun": {"content": "Hello "}},
                                {"textRun": {"content": "World\n"}},
                            ]
                        }
                    },
                    {
                        "paragraph": {
                            "elements": [
                                {"textRun": {"content": "Second paragraph\n"}},
                            ]
                        }
                    },
                ]
            },
        }

        with patch.object(client, "_build_service", return_value=mock_docs_service):
            result = await client.read_document("doc-789")

        assert isinstance(result, DocReadResult)
        assert result.document_id == "doc-789"
        assert result.title == "Test Doc"
        assert result.body_text == "Hello World\nSecond paragraph\n"
        assert result.revision_id == "rev-1"

    @pytest.mark.asyncio
    async def test_handles_empty_document(self, client, mock_docs_service):
        mock_docs_service.documents().get().execute.return_value = {
            "documentId": "doc-empty",
            "title": "Empty",
            "body": {"content": []},
        }

        with patch.object(client, "_build_service", return_value=mock_docs_service):
            result = await client.read_document("doc-empty")

        assert result.body_text == ""
        assert result.revision_id is None


class TestAppendText:
    @pytest.mark.asyncio
    async def test_appends_text_at_end_of_document(self, client, mock_docs_service):
        # First call: get document to find end index
        mock_docs_service.documents().get().execute.return_value = {
            "title": "Existing Doc",
            "body": {
                "content": [
                    {"endIndex": 15},
                ]
            },
        }
        # Second call: batchUpdate
        mock_docs_service.documents().batchUpdate().execute.return_value = {
            "replies": [{}],
        }

        with patch.object(client, "_build_service", return_value=mock_docs_service):
            result = await client.append_text("doc-100", "\nNew text")

        assert isinstance(result, DocWriteResult)
        assert result.document_id == "doc-100"
        assert result.title == "Existing Doc"
        assert result.replies == 1


class TestReplaceText:
    @pytest.mark.asyncio
    async def test_replaces_text_in_document(self, client, mock_docs_service):
        mock_docs_service.documents().batchUpdate().execute.return_value = {
            "replies": [{}],
        }
        mock_docs_service.documents().get().execute.return_value = {
            "title": "Updated Doc",
        }

        with patch.object(client, "_build_service", return_value=mock_docs_service):
            result = await client.replace_text("doc-200", "old text", "new text")

        assert isinstance(result, DocWriteResult)
        assert result.document_id == "doc-200"
        assert result.title == "Updated Doc"
        assert result.replies == 1


class TestListDocuments:
    @pytest.mark.asyncio
    async def test_lists_documents_from_drive(self, client, mock_drive_service):
        mock_drive_service.files().list().execute.return_value = {
            "files": [
                {
                    "id": "doc-a",
                    "name": "Meeting Notes",
                    "webViewLink": "https://docs.google.com/document/d/doc-a/edit",
                    "modifiedTime": "2026-03-15T10:00:00Z",
                },
                {
                    "id": "doc-b",
                    "name": "Project Plan",
                    "modifiedTime": "2026-03-14T08:30:00Z",
                },
            ]
        }

        with patch.object(client, "_build_drive_service", return_value=mock_drive_service):
            result = await client.list_documents(max_results=10)

        assert len(result) == 2
        assert result[0]["document_id"] == "doc-a"
        assert result[0]["title"] == "Meeting Notes"
        assert result[0]["url"] == "https://docs.google.com/document/d/doc-a/edit"
        assert result[1]["document_id"] == "doc-b"
        assert "docs.google.com/document/d/doc-b" in result[1]["url"]

    @pytest.mark.asyncio
    async def test_handles_empty_results(self, client, mock_drive_service):
        mock_drive_service.files().list().execute.return_value = {"files": []}

        with patch.object(client, "_build_drive_service", return_value=mock_drive_service):
            result = await client.list_documents()

        assert result == []


class TestExtractBodyText:
    def test_extracts_from_paragraphs(self):
        doc = {
            "body": {
                "content": [
                    {
                        "paragraph": {
                            "elements": [
                                {"textRun": {"content": "Line 1\n"}},
                            ]
                        }
                    },
                    {
                        "sectionBreak": {}
                    },
                    {
                        "paragraph": {
                            "elements": [
                                {"textRun": {"content": "Line 2\n"}},
                                {"inlineObjectElement": {}},
                            ]
                        }
                    },
                ]
            }
        }
        assert GoogleDocsClient._extract_body_text(doc) == "Line 1\nLine 2\n"

    def test_empty_body(self):
        assert GoogleDocsClient._extract_body_text({}) == ""
        assert GoogleDocsClient._extract_body_text({"body": {}}) == ""
        assert GoogleDocsClient._extract_body_text({"body": {"content": []}}) == ""
