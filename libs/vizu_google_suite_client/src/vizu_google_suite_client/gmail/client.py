"""Gmail Client implementation"""
from typing import List, Optional
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from ..base import BaseGoogleClient
from .models import EmailMessage, SendResult


class GoogleGmailClient(BaseGoogleClient):
    """Gmail API client with proper implementation."""

    def _build_service(self):
        try:
            from googleapiclient.discovery import build  # type: ignore
        except ImportError:
            raise ImportError("google-api-python-client not installed; install it to use Gmail client")

        creds = self._get_credentials()
        return build("gmail", "v1", credentials=creds, cache_discovery=False)

    async def search_messages(self, query: str, max_results: int = 10, label_ids: Optional[List[str]] = None) -> List[EmailMessage]:
        """Search Gmail messages matching query."""
        service = self._build_service()
        user_id = "me"

        # Build list request
        request_params = {"userId": user_id, "q": query, "maxResults": max_results}
        if label_ids:
            request_params["labelIds"] = label_ids

        resp = service.users().messages().list(**request_params).execute()
        msgs = resp.get("messages", [])

        results = []
        for m in msgs[:max_results]:
            full = service.users().messages().get(userId=user_id, id=m["id"], format="full").execute()
            # Parse headers
            headers = {h["name"]: h["value"] for h in full.get("payload", {}).get("headers", [])}
            results.append(EmailMessage(
                id=full["id"],
                thread_id=full.get("threadId"),
                subject=headers.get("Subject", ""),
                sender=headers.get("From", ""),
                to=headers.get("To", ""),
                date=headers.get("Date", ""),
                snippet=full.get("snippet", ""),
                body=self._extract_body(full),
                labels=full.get("labelIds", []),
            ))
        return results

    def _extract_body(self, message: dict) -> str:
        """Extract plain text body from Gmail message."""
        payload = message.get("payload", {})

        # Check for simple message
        if "body" in payload and payload["body"].get("data"):
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")

        # Check multipart
        parts = payload.get("parts", [])
        for part in parts:
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")

        return ""

    async def get_message(self, message_id: str) -> EmailMessage:
        """Get a single message by ID."""
        service = self._build_service()
        full = service.users().messages().get(userId="me", id=message_id, format="full").execute()
        headers = {h["name"]: h["value"] for h in full.get("payload", {}).get("headers", [])}
        return EmailMessage(
            id=full["id"],
            thread_id=full.get("threadId"),
            subject=headers.get("Subject", ""),
            sender=headers.get("From", ""),
            to=headers.get("To", ""),
            date=headers.get("Date", ""),
            snippet=full.get("snippet", ""),
            body=self._extract_body(full),
            labels=full.get("labelIds", []),
        )

    async def send_message(
        self,
        to: List[str],
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> SendResult:
        """Send an email message."""
        service = self._build_service()

        if body_html:
            message = MIMEMultipart("alternative")
            message.attach(MIMEText(body_text, "plain"))
            message.attach(MIMEText(body_html, "html"))
        else:
            message = MIMEText(body_text)

        message["to"] = ", ".join(to)
        message["subject"] = subject
        if cc:
            message["cc"] = ", ".join(cc)
        if bcc:
            message["bcc"] = ", ".join(bcc)

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        result = service.users().messages().send(userId="me", body={"raw": raw}).execute()

        return SendResult(message_id=result["id"], thread_id=result.get("threadId"))
