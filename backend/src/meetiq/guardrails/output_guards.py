import re

from meetiq.core.logging import logger

# Patterns that suggest a suspiciously specific claim
# These are facts the model might hallucinate (exact numbers not in sources)
HALLUCINATION_PATTERNS = [
    # Revenue / ARR figures: "$12M ARR", "$400 million revenue"
    (r"\$[\d,]+\.?\d*\s*[BMK]?\s*(ARR|MRR|revenue|annual recurring)", "revenue_figure"),

    # Headcount: "500 employees", "1,200 staff"
    (r"\b[\d,]{2,}\s*(employees|staff|headcount|team members|engineers|people)\b", "headcount"),

    # Funding: "$50M Series B" — specific dollar + round
    (r"\$[\d,]+\.?\d*\s*[BM]?\s*(Series [A-Z]|seed|pre-seed|funding round)", "funding_figure"),

    # Specific dates that look precise: "founded in 2019", "launched on March 12"
    (r"(founded|launched|established)\s+(in|on)\s+\d{4}", "founding_date"),

    # Valuations: "$1.2B valuation", "valued at $400M"
    (r"(valuation|valued at)\s+\$[\d,]+\.?\d*\s*[BM]?", "valuation"),
]

_COMPILED_PATTERNS = [
    (re.compile(pattern, re.IGNORECASE), label)
    for pattern, label in HALLUCINATION_PATTERNS
]


def _brief_as_text(brief: dict) -> str:
    """Flatten all brief string values into one text block for scanning."""
    parts = []
    for value in brief.values():
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            parts.extend(str(item) for item in value)
    return " ".join(parts)


def check_hallucinations(brief: dict, source_material: str) -> list[str]:
    """
    Scan the brief for specific claims, then check if each claim
    actually appears in the raw source material we collected.

    Why we do this:
    - LLMs confidently state numbers that aren't in the sources
    - "$50M Series B" sounds specific but might be invented or from a different company
    - If the number isn't in our scraped/searched text, we flag it

    Returns a list of warning strings (empty = no flags).
    """
    brief_text = _brief_as_text(brief)
    flags = []

    for pattern, label in _COMPILED_PATTERNS:
        matches = pattern.findall(brief_text)
        for match in matches:
            # match might be a tuple (from groups) or a string
            match_text = match if isinstance(match, str) else " ".join(m for m in match if m)
            # Check if this specific text appears in what we actually gathered
            if match_text and match_text.lower() not in source_material.lower():
                flag_msg = f"Unverified {label}: '{match_text}' not found in sources"
                flags.append(flag_msg)
                logger.warning("hallucination_flag",
                               label=label,
                               claim=match_text[:80],
                               company=brief.get("description", "")[:40])

    return flags


def validate_brief_schema(brief: dict) -> tuple[bool, list[str]]:
    """
    Check that the brief has all required fields and they're non-empty.

    Returns (is_valid, list_of_problems).

    Why Pydantic isn't enough here:
    - Pydantic validates types but not semantic emptiness
    - A brief with description="" passes Pydantic but is useless
    - We want to catch "the LLM returned an empty brief" as a failure
    """
    problems = []
    required = {
        "description": str,
        "recent_news": list,
        "tech_signals": list,
        "pain_points": list,
        "talking_points": list,
        "sources_used": list,
    }

    for field, expected_type in required.items():
        if field not in brief:
            problems.append(f"Missing field: '{field}'")
        elif not isinstance(brief[field], expected_type):
            problems.append(f"Wrong type for '{field}': expected {expected_type.__name__}")
        elif expected_type == str and not brief[field].strip():
            problems.append(f"Empty string for required field '{field}'")
        elif expected_type == list and len(brief[field]) == 0 and field == "talking_points":
            # talking_points is the most critical — flag if empty
            problems.append("talking_points is empty — brief is not actionable")

    if problems:
        logger.warning("brief_schema_invalid", problems=problems)

    return len(problems) == 0, problems


def validate_output(brief: dict, source_material: str) -> tuple[bool, list[str]]:
    """
    Full output validation: schema check + hallucination scan.

    Call this after synthesis_node produces a brief.
    Returns (is_valid, all_issues) where is_valid = schema OK AND no hallucinations.
    """
    schema_ok, schema_issues = validate_brief_schema(brief)
    hallucination_flags = check_hallucinations(brief, source_material)

    all_issues = schema_issues + hallucination_flags
    is_valid = schema_ok and len(hallucination_flags) == 0

    if all_issues:
        logger.info("output_validation_complete",
                    schema_ok=schema_ok,
                    hallucination_count=len(hallucination_flags),
                    total_issues=len(all_issues))

    return is_valid, all_issues
