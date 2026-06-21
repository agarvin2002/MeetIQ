import asyncio

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse

from meetiq.cache.brief_cache import brief_cache
from meetiq.core.logging import logger
from meetiq.models.brief import MeetingCard
from meetiq.services.calendar_service import get_upcoming_meetings
from meetiq.services.company_extractor import extract_company
from meetiq.services.research_service import research_company

router = APIRouter()


async def _research_and_update_cache(company_name: str, domain: str | None, cache_key: str) -> None:
    """
    Background task: run research and store result in cache.

    This runs AFTER we've already returned the "researching" card to the user.
    The frontend polls every 60s — by then, this will usually be done.
    """
    try:
        brief = await research_company(company_name, domain)
        brief_cache.set(cache_key, brief)
        logger.info("background_research_complete", company=company_name, cache_key=cache_key)
    except Exception as e:
        logger.error("background_research_failed", company=company_name, error=str(e)[:100])


@router.get("/", response_model=list[MeetingCard])
async def get_meetings(request: Request, background_tasks: BackgroundTasks):
    """
    Returns all upcoming meetings (next 7 days) with research briefs.

    Flow:
    1. Authenticate via session token
    2. Fetch meetings from Google Calendar
    3. For each meeting, extract company identity
    4. If cached → attach brief immediately (status: "ready")
    5. If not cached → return card with status "researching", kick off background research
    6. If company unknown → return card with status "unidentified"

    The frontend polls this endpoint every 60s, so "researching" cards
    will flip to "ready" on the next poll when background research completes.
    """
    token_data = request.session.get("token")
    if not token_data:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    # ── Fetch meetings from Google Calendar ────────────────────────────────
    try:
        meetings = await get_upcoming_meetings(token_data)
    except Exception as e:
        logger.error("calendar_fetch_failed", error=str(e)[:100])
        return JSONResponse(status_code=502, content={"error": "Could not fetch calendar"})

    logger.info("meetings_fetched", count=len(meetings))

    # ── Build cards ────────────────────────────────────────────────────────
    cards = []

    for meeting in meetings:
        company_name, domain = extract_company(meeting)
        cache_key = domain or (company_name.lower() if company_name else None)

        # Scenario C: company not identified
        if company_name is None:
            cards.append(MeetingCard(
                id=meeting.id,
                title=meeting.title,
                start_time=meeting.start_time,
                end_time=meeting.end_time,
                attendees=meeting.attendees,
                company_identified=False,
                brief_status="unidentified",
            ))
            continue

        # Check cache first
        cached_brief = brief_cache.get(cache_key) if cache_key else None

        if cached_brief is not None:
            # Research already done — serve immediately
            cards.append(MeetingCard(
                id=meeting.id,
                title=meeting.title,
                start_time=meeting.start_time,
                end_time=meeting.end_time,
                attendees=meeting.attendees,
                company_identified=True,
                company_name=company_name,
                company_domain=domain,
                brief_status="ready",
                brief=cached_brief,
            ))
        else:
            # Not cached — return "researching" card and kick off background research
            cards.append(MeetingCard(
                id=meeting.id,
                title=meeting.title,
                start_time=meeting.start_time,
                end_time=meeting.end_time,
                attendees=meeting.attendees,
                company_identified=True,
                company_name=company_name,
                company_domain=domain,
                brief_status="researching",
                brief=None,
            ))
            # Add background task — runs after response is sent
            background_tasks.add_task(
                _research_and_update_cache,
                company_name,
                domain,
                cache_key,
            )

    logger.info("meetings_response_built",
                total=len(cards),
                ready=sum(1 for c in cards if c.brief_status == "ready"),
                researching=sum(1 for c in cards if c.brief_status == "researching"),
                unidentified=sum(1 for c in cards if c.brief_status == "unidentified"))

    return cards


@router.post("/{meeting_id}/refresh", response_model=MeetingCard)
async def refresh_meeting(meeting_id: str, request: Request, background_tasks: BackgroundTasks):
    """
    Force re-research a specific meeting — invalidates cache and kicks off fresh research.

    Used by the "Refresh" button in the frontend.
    Returns the card immediately with status "researching" — next poll brings fresh data.
    """
    token_data = request.session.get("token")
    if not token_data:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    try:
        meetings = await get_upcoming_meetings(token_data)
    except Exception as e:
        return JSONResponse(status_code=502, content={"error": "Could not fetch calendar"})

    # Find the specific meeting
    meeting = next((m for m in meetings if m.id == meeting_id), None)
    if not meeting:
        return JSONResponse(status_code=404, content={"error": "Meeting not found"})

    company_name, domain = extract_company(meeting)
    if not company_name:
        return JSONResponse(status_code=400, content={"error": "Cannot identify company for this meeting"})

    cache_key = domain or company_name.lower()

    # Invalidate cache so fresh research runs
    brief_cache.delete(cache_key)
    logger.info("cache_invalidated", company=company_name, cache_key=cache_key)

    # Kick off fresh research in background
    background_tasks.add_task(_research_and_update_cache, company_name, domain, cache_key)

    return MeetingCard(
        id=meeting.id,
        title=meeting.title,
        start_time=meeting.start_time,
        end_time=meeting.end_time,
        attendees=meeting.attendees,
        company_identified=True,
        company_name=company_name,
        company_domain=domain,
        brief_status="researching",
        brief=None,
    )
