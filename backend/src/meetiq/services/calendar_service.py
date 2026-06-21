from datetime import datetime, timezone, timedelta

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from meetiq.core.logging import logger
from meetiq.models.meeting import Meeting

# Personal email domains — if ALL attendees use these, we can't identify the company
PERSONAL_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "icloud.com", "me.com", "protonmail.com", "live.com",
    "aol.com", "yahoo.in", "rediffmail.com",
}


def is_personal_domain(domain: str) -> bool:
    return domain.lower() in PERSONAL_EMAIL_DOMAINS


def build_credentials(token_data: dict) -> Credentials:
    """Reconstruct Google credentials from session-stored token dict."""
    return Credentials(
        token=token_data["token"],
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data["token_uri"],
        client_id=token_data["client_id"],
        client_secret=token_data["client_secret"],
        scopes=token_data["scopes"],
    )


async def get_upcoming_meetings(token_data: dict) -> list[Meeting]:
    """
    Fetch upcoming meetings from Google Calendar for today + next 7 days.

    Extracts: title, start/end time, attendee emails.
    Filters out: events with no attendees, declined events, all-day events.
    """
    credentials = build_credentials(token_data)

    # Build the Calendar API client
    service = build("calendar", "v3", credentials=credentials)

    # Time range: now → 7 days from now
    now = datetime.now(timezone.utc)
    week_later = now + timedelta(days=7)

    # Call the Calendar API
    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now.isoformat(),
            timeMax=week_later.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=20,
        )
        .execute()
    )

    events = events_result.get("items", [])
    meetings = []

    for event in events:
        # Skip all-day events (they have "date" not "dateTime")
        start = event.get("start", {})
        if "date" in start and "dateTime" not in start:
            continue

        # Skip events the user declined
        my_status = event.get("attendees", [{}])
        for attendee in my_status:
            if attendee.get("self") and attendee.get("responseStatus") == "declined":
                continue

        # Extract attendee emails (excluding the calendar owner themselves)
        attendees = [
            a["email"]
            for a in event.get("attendees", [])
            if not a.get("self", False) and a.get("email")
        ]

        meeting = Meeting(
            id=event["id"],
            title=event.get("summary", "Untitled Meeting"),
            start_time=start.get("dateTime", ""),
            end_time=event.get("end", {}).get("dateTime", ""),
            attendees=attendees,
            description=event.get("description"),
        )
        meetings.append(meeting)

    logger.info("calendar_fetch_complete", meeting_count=len(meetings))
    return meetings
