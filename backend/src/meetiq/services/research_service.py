import asyncio
import time
from langchain_core.messages import ToolMessage

from meetiq.agents.research_graph import GRAPH_CONFIG, research_graph
from meetiq.cache.brief_cache import brief_cache
from meetiq.config.settings import settings
from meetiq.core.logging import logger
from meetiq.guardrails.input_guards import validate_research_inputs
from meetiq.guardrails.output_guards import validate_output
from meetiq.models.brief import ResearchBrief


def _collect_source_material(state: dict) -> str:
    """
    Extract all raw text returned by tools during the research run.

    We need this text to cross-check the brief for hallucinations.
    ToolMessages are the responses from each tool call — they contain
    the actual scraped/searched content that Gemini synthesized from.
    """
    parts = []
    for msg in state.get("messages", []):
        # ToolMessage = result of a tool call (has tool_call_id)
        if isinstance(msg, ToolMessage):
            parts.append(msg.content)
    return "\n\n".join(parts)


async def research_company(company_name: str, domain: str | None) -> ResearchBrief:
    """
    Full research pipeline for one company. Steps:

    1. Check cache — return immediately if we have a recent brief
    2. Sanitize inputs via input guards
    3. Run LangGraph research agent with a hard timeout
    4. Extract source material from tool results
    5. Validate output via output guards
    6. Store in cache
    7. Return ResearchBrief

    This function never raises — on any failure it returns a partial/fallback brief.
    """
    cache_key = domain or company_name.lower()

    # ── 1. Cache check ─────────────────────────────────────────────────────
    cached = brief_cache.get(cache_key)
    if cached is not None:
        logger.info("cache_hit", company=company_name, key=cache_key)
        return cached

    # ── 2. Input guardrails ────────────────────────────────────────────────
    clean_name, clean_domain = validate_research_inputs(company_name, domain)
    if clean_name is None:
        logger.warning("research_skipped_bad_input", company=company_name[:60])
        return _fallback_brief(company_name, reason="Input failed guardrails")

    start = time.time()
    logger.info("research_started", company=clean_name, domain=clean_domain)

    # ── 3. Run the agent with a hard timeout ───────────────────────────────
    # research_timeout_s is set in .env (default 60s).
    # If the agent takes longer — e.g. Gemini is slow — we cancel and return
    # whatever partial data we have rather than blocking the user forever.
    try:
        result = await asyncio.wait_for(
            research_graph.ainvoke(
                {
                    "messages": [],
                    "company_name": clean_name,
                    "domain": clean_domain,
                    "brief": None,
                },
                config=GRAPH_CONFIG,
            ),
            timeout=settings.research_timeout_s,
        )
    except asyncio.TimeoutError:
        elapsed = round(time.time() - start)
        logger.warning("research_timeout", company=clean_name, elapsed_s=elapsed)
        return _fallback_brief(clean_name, reason=f"Research timed out after {elapsed}s", partial=True)
    except Exception as e:
        logger.error("research_failed", company=clean_name, error=str(e)[:200])
        return _fallback_brief(clean_name, reason=str(e)[:100], partial=True)

    # ── 4. Extract raw source material for hallucination check ─────────────
    source_material = _collect_source_material(result)

    # ── 5. Output guardrails ───────────────────────────────────────────────
    raw_brief = result.get("brief") or {}
    is_valid, issues = validate_output(raw_brief, source_material)

    if issues:
        logger.warning("brief_has_issues",
                       company=clean_name,
                       issues=issues,
                       issue_count=len(issues))
        # We don't discard the brief — we mark it partial and log the flags.
        # A flagged brief is better than no brief.
        raw_brief["partial"] = True

    # ── 6. Build validated model ───────────────────────────────────────────
    try:
        brief = ResearchBrief(**raw_brief)
    except Exception as e:
        logger.error("brief_model_error", company=clean_name, error=str(e))
        return _fallback_brief(clean_name, reason="Brief validation failed", partial=True)

    # ── 7. Cache + log ─────────────────────────────────────────────────────
    duration_ms = round((time.time() - start) * 1000)
    logger.info("research_complete",
                company=clean_name,
                duration_ms=duration_ms,
                partial=brief.partial,
                sources=len(brief.sources_used))

    brief_cache.set(cache_key, brief)
    return brief


def _fallback_brief(company_name: str, reason: str = "", partial: bool = False) -> ResearchBrief:
    """
    Return a minimal valid brief when research fails or times out.

    Why return this instead of raising:
    - The /meetings endpoint should always return cards, never 500
    - A card with "research unavailable" is better than a broken page
    - The frontend shows a retry button when brief_status = "failed"
    """
    return ResearchBrief(
        description=f"Research for {company_name} is currently unavailable. {reason}".strip(),
        recent_news=[],
        tech_signals=[],
        pain_points=[],
        talking_points=[
            f"Ask {company_name} about their current priorities.",
            "Discuss how your product could solve their challenges.",
        ],
        sources_used=[],
        partial=partial,
    )
