from pydantic import BaseModel
from typing import Optional


class Meeting(BaseModel):
    """Represents a single Google Calendar event."""
    id: str                          # Google's unique event ID
    title: str                       # Event title e.g. "Demo call with Linear"
    start_time: str                  # ISO format: "2026-06-21T14:00:00Z"
    end_time: str
    attendees: list[str]             # List of attendee emails
    description: Optional[str] = None  # Event description (may contain URLs/context)
