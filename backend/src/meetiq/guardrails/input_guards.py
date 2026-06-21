import re
from urllib.parse import urlparse

from meetiq.core.logging import logger

# Patterns that suggest someone is trying to hijack the LLM via meeting titles
# These are common prompt injection phrases
INJECTION_PATTERNS = [
    r"ignore\s+(previous|all|above)\s+instructions?",
    r"system\s+prompt",
    r"you\s+are\s+now",
    r"jailbreak",
    r"forget\s+everything",
    r"act\s+as\s+(if\s+you\s+are|a)",
    r"disregard\s+(all|previous|above)",
    r"new\s+instructions?:",
    r"<\s*system\s*>",              # XML-style system tag injection
    r"\[INST\]",                    # LLaMA instruction token injection
]

_INJECTION_RE = re.compile(
    "|".join(INJECTION_PATTERNS),
    flags=re.IGNORECASE,
)


def sanitize_company_name(name: str) -> str | None:
    """
    Clean and validate a company name before passing to the agent.

    Returns the sanitized name, or None if the input is dangerous.

    Why return None instead of "[sanitized]":
    - If we can't identify the company, we should skip research entirely
    - Returning a fake name could cause the agent to research the wrong company
    """
    if not name or not name.strip():
        return None

    # Truncate to sane length — company names are never 500 chars
    name = name.strip()[:200]

    # Check for prompt injection
    if _INJECTION_RE.search(name):
        logger.warning("prompt_injection_detected",
                       input_snippet=name[:60],
                       source="company_name")
        return None

    return name


def sanitize_domain(domain: str) -> str | None:
    """
    Reduce a domain string to a bare hostname.

    Why this matters:
    - A malicious meeting could have domain "evil.com/</script><script>alert(1)"
    - Or "linear.app/../../../etc/passwd" (path traversal — useless here but bad habit)
    - We only want the hostname: "linear.app"

    Returns None if the domain looks completely invalid.
    """
    if not domain or not domain.strip():
        return None

    domain = domain.strip()

    # Add scheme if missing so urlparse works correctly
    if not domain.startswith(("http://", "https://")):
        domain = f"https://{domain}"

    try:
        parsed = urlparse(domain)
        hostname = parsed.netloc or parsed.path  # netloc is empty if no scheme was there
        # Strip port if present (e.g. "linear.app:443" → "linear.app")
        hostname = hostname.split(":")[0].lower()
        # Must look like a real domain: at least one dot, only valid chars
        if not hostname or "." not in hostname:
            return None
        if not re.match(r"^[a-z0-9.-]+$", hostname):
            logger.warning("invalid_domain_chars", domain=hostname[:60])
            return None
        return hostname
    except Exception:
        return None


def validate_research_inputs(company_name: str, domain: str | None) -> tuple[str | None, str | None]:
    """
    Central entry point: validate both inputs before research starts.

    Returns (clean_company_name, clean_domain) — either can be None.
    If company_name is None, caller should skip research entirely.
    """
    clean_name = sanitize_company_name(company_name)
    clean_domain = sanitize_domain(domain) if domain else None

    if clean_name is None:
        logger.warning("research_inputs_rejected",
                       company_name=company_name[:60] if company_name else "",
                       reason="injection_or_empty")

    return clean_name, clean_domain
