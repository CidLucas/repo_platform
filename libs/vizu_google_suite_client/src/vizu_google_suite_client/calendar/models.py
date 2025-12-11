
from pydantic import BaseModel


class CalendarEvent(BaseModel):
    """Google Calendar event model."""
    id: str
    summary: str = ""
    description: str | None = None
    start: str  # ISO datetime string
    end: str  # ISO datetime string
    location: str | None = None
    attendees: list[str] | None = None  # List of email addresses
    status: str = ""
    html_link: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "summary": self.summary,
            "description": self.description,
            "start": self.start,
            "end": self.end,
            "location": self.location,
            "attendees": self.attendees,
            "status": self.status,
            "html_link": self.html_link,
        }
