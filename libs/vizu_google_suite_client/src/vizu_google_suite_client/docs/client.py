"""Google Docs Client implementation"""

from ..base import BaseGoogleClient
from .models import DocReadResult, DocWriteResult


class GoogleDocsClient(BaseGoogleClient):
    """Google Docs API v1 client."""

    def _build_service(self):
        try:
            from googleapiclient.discovery import build  # type: ignore
        except ImportError:
            raise ImportError("google-api-python-client not installed; install it to use Docs client")

        creds = self._get_credentials()
        return build("docs", "v1", credentials=creds, cache_discovery=False)

    def _build_drive_service(self):
        try:
            from googleapiclient.discovery import build  # type: ignore
        except ImportError:
            raise ImportError("google-api-python-client not installed; install it to use Docs client")

        creds = self._get_credentials()
        return build("drive", "v3", credentials=creds, cache_discovery=False)

    @staticmethod
    def _extract_body_text(document: dict) -> str:
        """Extract plain text from a Google Docs document body structure."""
        body = document.get("body", {})
        content = body.get("content", [])
        parts: list[str] = []
        for element in content:
            paragraph = element.get("paragraph")
            if not paragraph:
                continue
            for pe in paragraph.get("elements", []):
                text_run = pe.get("textRun")
                if text_run:
                    parts.append(text_run.get("content", ""))
        return "".join(parts)

    async def create_document(self, title: str) -> dict:
        """Create a new Google Doc and return its ID and URL."""
        service = self._build_service()
        body = {"title": title}
        doc = service.documents().create(body=body).execute()
        doc_id = doc.get("documentId", "")
        return {
            "document_id": doc_id,
            "document_url": f"https://docs.google.com/document/d/{doc_id}/edit",
            "title": doc.get("title", title),
        }

    async def read_document(self, document_id: str) -> DocReadResult:
        """Read a document and return its plain-text content."""
        service = self._build_service()
        doc = service.documents().get(documentId=document_id).execute()
        return DocReadResult(
            document_id=document_id,
            title=doc.get("title", ""),
            body_text=self._extract_body_text(doc),
            revision_id=doc.get("revisionId"),
        )

    async def append_text(self, document_id: str, text: str) -> DocWriteResult:
        """Append text at the end of the document."""
        service = self._build_service()

        # The Docs API requires inserting at a specific index.
        # Index 1 is the start of the body; to append, we need the end index.
        doc = service.documents().get(documentId=document_id).execute()
        body_content = doc.get("body", {}).get("content", [])
        # The last structural element's endIndex gives us the insertion point
        end_index = 1
        if body_content:
            end_index = body_content[-1].get("endIndex", 1) - 1

        requests = [
            {
                "insertText": {
                    "location": {"index": end_index},
                    "text": text,
                }
            }
        ]
        result = service.documents().batchUpdate(
            documentId=document_id,
            body={"requests": requests},
        ).execute()
        return DocWriteResult(
            document_id=document_id,
            title=doc.get("title", ""),
            replies=len(result.get("replies", [])),
        )

    async def replace_text(
        self, document_id: str, old_text: str, new_text: str
    ) -> DocWriteResult:
        """Replace all occurrences of old_text with new_text in the document."""
        service = self._build_service()

        requests = [
            {
                "replaceAllText": {
                    "containsText": {
                        "text": old_text,
                        "matchCase": True,
                    },
                    "replaceText": new_text,
                }
            }
        ]
        result = service.documents().batchUpdate(
            documentId=document_id,
            body={"requests": requests},
        ).execute()

        # Fetch the title after the update
        doc = service.documents().get(
            documentId=document_id, fields="title"
        ).execute()

        return DocWriteResult(
            document_id=document_id,
            title=doc.get("title", ""),
            replies=len(result.get("replies", [])),
        )

    async def list_documents(self, max_results: int = 20) -> list[dict]:
        """List user's recent Google Docs from Drive."""
        drive_service = self._build_drive_service()

        query = "mimeType='application/vnd.google-apps.document' and trashed=false"
        results = drive_service.files().list(
            q=query,
            pageSize=max_results,
            fields="files(id, name, webViewLink, modifiedTime)",
            orderBy="modifiedTime desc",
        ).execute()

        files = results.get("files", [])
        return [
            {
                "document_id": f["id"],
                "title": f["name"],
                "url": f.get("webViewLink", f"https://docs.google.com/document/d/{f['id']}/edit"),
                "modified_time": f.get("modifiedTime"),
            }
            for f in files
        ]
