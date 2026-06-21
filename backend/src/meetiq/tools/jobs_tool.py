import asyncio
import time

from langchain_core.tools import tool

from meetiq.config.settings import settings
from meetiq.core.logging import logger
from meetiq.tools.base import CircuitBreaker
from meetiq.tools.tavily_tool import _tavily_cb, _tavily_search, _format_results


@tool
async def search_job_listings(company: str) -> str:
    """
    Search job listings for a company to infer their tech stack, team size,
    and growth signals. Job descriptions reveal what technologies they use
    even when not publicly stated.
    Use this to find: programming languages, frameworks, cloud providers,
    databases, and tools the company uses internally.
    Good signals: "Senior React Engineer", "AWS experience required",
    "experience with Kubernetes", "PostgreSQL at scale".
    """
    if _tavily_cb.is_open():
        return "Job search unavailable — circuit breaker open."

    # Target job boards directly for better signal
    query = f"{company} jobs hiring engineer developer 2025 site:linkedin.com OR site:lever.co OR site:greenhouse.io"

    start = time.time()
    try:
        results = await asyncio.wait_for(
            _tavily_search(query, max_results=4),
            timeout=settings.tavily_timeout_s
        )
        duration_ms = round((time.time() - start) * 1000)
        logger.info("tool_call", tool="search_job_listings", company=company,
                    results_count=len(results), duration_ms=duration_ms)
        _tavily_cb.record_success()

        if not results:
            # Fallback: generic job search without site filter
            results = await _tavily_search(f"{company} is hiring engineering roles tech stack", max_results=3)

        return _format_results(results)

    except asyncio.TimeoutError:
        logger.error("tool_timeout", tool="search_job_listings")
        return "Job listings search timed out."

    except Exception as e:
        logger.error("tool_failed", tool="search_job_listings", error=str(e)[:100])
        return f"Job listings search failed: {str(e)[:100]}"
