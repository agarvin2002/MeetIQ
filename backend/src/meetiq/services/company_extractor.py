import re

from meetiq.core.logging import logger
from meetiq.models.meeting import Meeting

# Free email providers — attendees on these are personal, not company reps
PERSONAL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "icloud.com", "me.com", "protonmail.com", "live.com",
    "aol.com", "msn.com", "ymail.com", "googlemail.com",
}

# Common meeting title patterns that contain a company name
# e.g. "Demo call with Linear", "Stripe <> Freehand sync"
_TITLE_PATTERNS = [
    re.compile(r"(?:call|demo|meeting|sync|intro|chat)\s+with\s+([A-Z][A-Za-z0-9\s]{1,40})", re.IGNORECASE),
    re.compile(r"([A-Z][A-Za-z0-9]+)\s+[<>x×]{1,3}\s+[A-Z][A-Za-z0-9]+", re.IGNORECASE),  # "Stripe <> Freehand"
    re.compile(r"([A-Z][A-Za-z0-9]+)\s+(?:sales|partnership|discovery|kickoff|onboarding)", re.IGNORECASE),
]

# Regex to pull URLs out of meeting descriptions
_URL_RE = re.compile(r"https?://(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})")


def _domain_to_name(domain: str) -> str:
    """
    Best-effort: convert a domain to a readable company name.
    "linear.app" → "Linear"
    "stripe.com" → "Stripe"
    "figma.io"   → "Figma"
    """
    # Take the leftmost part before the TLD
    parts = domain.split(".")
    name = parts[0]
    # Remove common subdomains that aren't the company name
    if name in ("www", "app", "mail", "api", "go", "get"):
        name = parts[1] if len(parts) > 1 else name
    return name.capitalize()


def _is_personal(domain: str) -> bool:
    return domain.lower() in PERSONAL_DOMAINS


def extract_company(meeting: Meeting) -> tuple[str | None, str | None]:
    """
    Infer (company_name, domain) from a meeting using a priority chain.

    Priority:
    1. Non-personal attendee email domains  ← most reliable
    2. Company name pattern in meeting title
    3. URL found in meeting description
    4. None if all strategies fail

    Returns (None, None) if we can't identify the company.
    """
    meeting_id = meeting.id

    # ── Priority 1: attendee email domains ────────────────────────────────
    # Most reliable signal: if john@linear.app is attending, the company is Linear
    for attendee in meeting.attendees:
        if "@" not in attendee:
            continue
        domain = attendee.split("@")[-1].lower()
        if not _is_personal(domain):
            name = _domain_to_name(domain)
            logger.info("company_extracted",
                        method="email_domain",
                        domain=domain,
                        company=name,
                        meeting_id=meeting_id)
            return name, domain

    # ── Priority 2: title pattern matching ────────────────────────────────
    # "Demo call with Linear" → "Linear"
    for pattern in _TITLE_PATTERNS:
        match = pattern.search(meeting.title or "")
        if match:
            name = match.group(1).strip()
            logger.info("company_extracted",
                        method="title_regex",
                        company=name,
                        meeting_id=meeting_id)
            return name, None   # no domain — agent will search by name

    # ── Priority 3: URL in description ────────────────────────────────────
    desc = meeting.description or ""
    url_matches = _URL_RE.findall(desc)
    for domain in url_matches:
        if not _is_personal(domain) and "zoom" not in domain and "meet.google" not in domain:
            name = _domain_to_name(domain)
            logger.info("company_extracted",
                        method="description_url",
                        domain=domain,
                        company=name,
                        meeting_id=meeting_id)
            return name, domain

    # ── Not identified ─────────────────────────────────────────────────────
    logger.warning("company_not_identified",
                   meeting_id=meeting_id,
                   title=(meeting.title or "")[:60])
    return None, None
