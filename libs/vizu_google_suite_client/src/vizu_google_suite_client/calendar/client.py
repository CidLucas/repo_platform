"""Google Calendar Client implementation"""
from datetime import datetime

from ..base import BaseGoogleClient
from .models import CalendarEvent


class GoogleCalendarClient(BaseGoogleClient):
    """Google Calendar API client."""

    def _build_service(self):
        try:
            from googleapiclient.discovery import build  # type: ignore
        except ImportError:
            raise ImportError("google-api-python-client not installed; install it to use Calendar client")

        creds = self._get_credentials()
        return build("calendar", "v3", credentials=creds, cache_discovery=False)

    async def list_events(
        self,
        calendar_id: str,
        time_min: datetime,
        time_max: datetime,
        max_results: int = 100,
    ) -> list[CalendarEvent]:
        """List calendar events within a time range."""
        service = self._build_service()

        # Ensure datetimes have timezone info (use UTC Z suffix if naive)
        time_min_str = time_min.isoformat() + "Z" if time_min.tzinfo is None else time_min.isoformat()
        time_max_str = time_max.isoformat() + "Z" if time_max.tzinfo is None else time_max.isoformat()

        resp = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min_str,
            timeMax=time_max_str,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        items = resp.get("items", [])
        events = []
        for it in items:
            start = it.get("start", {})
            end = it.get("end", {})
            events.append(CalendarEvent(
                id=it.get("id", ""),
                summary=it.get("summary", ""),
                description=it.get("description"),
                start=start.get("dateTime") or start.get("date", ""),
                end=end.get("dateTime") or end.get("date", ""),
                location=it.get("location"),
                attendees=[a.get("email") for a in it.get("attendees", [])],
                status=it.get("status", ""),
                html_link=it.get("htmlLink"),
            ))
        return events

    async def create_event(
        self,
        calendar_id: str,
        summary: str,
        start: datetime,
        end: datetime,
        description: str | None = None,
        attendees: list[str] | None = None,
        location: str | None = None,
    ) -> CalendarEvent:
        """Create a new calendar event."""
        service = self._build_service()

        body = {
            "summary": summary,
            "start": {"dateTime": start.isoformat() + "Z" if start.tzinfo is None else start.isoformat()},
            "end": {"dateTime": end.isoformat() + "Z" if end.tzinfo is None else end.isoformat()},
        }
        if description:
            body["description"] = description
        if location:
            body["location"] = location
        if attendees:
            body["attendees"] = [{"email": a} for a in attendees]

        ev = service.events().insert(calendarId=calendar_id, body=body).execute()

        start_resp = ev.get("start", {})
        end_resp = ev.get("end", {})
        return CalendarEvent(
            id=ev.get("id", ""),
            summary=ev.get("summary", ""),
            description=ev.get("description"),
            start=start_resp.get("dateTime") or start_resp.get("date", ""),
            end=end_resp.get("dateTime") or end_resp.get("date", ""),
            location=ev.get("location"),
            attendees=[a.get("email") for a in ev.get("attendees", [])],
            status=ev.get("status", ""),
            html_link=ev.get("htmlLink"),
        )

    async def get_event(self, calendar_id: str, event_id: str) -> CalendarEvent:
        """Get a single calendar event by ID."""
        service = self._build_service()
        ev = service.events().get(calendarId=calendar_id, eventId=event_id).execute()

        start = ev.get("start", {})
        end = ev.get("end", {})
        return CalendarEvent(
            id=ev.get("id", ""),
            summary=ev.get("summary", ""),
            description=ev.get("description"),
            start=start.get("dateTime") or start.get("date", ""),
            end=end.get("dateTime") or end.get("date", ""),
            location=ev.get("location"),
            attendees=[a.get("email") for a in ev.get("attendees", [])],
            status=ev.get("status", ""),
            html_link=ev.get("htmlLink"),
        )
