import asyncio
import time

from langchain_core.tools import tool
from tavily import TavilyClient

from meetiq.config.settings import settings
from meetiq.core.logging import logger
from meetiq.tools.base import CircuitBreaker, with_retry

# One circuit breaker shared across all Tavily calls
_tavily_cb = CircuitBreaker(name="tavily")
_client = TavilyClient(api_key=settings.tavily_api_key)


def _format_results(results: list[dict]) -> str:
    """Convert Tavily result list into clean text the agent can read."""
    if not results:
        return "No results found."
    lines = []
    for r in results:
        lines.append(f"Source: {r.get('url', 'unknown')}")
        lines.append(f"Title: {r.get('title', '')}")
        lines.append(f"Content: {r.get('content', '')[:500]}")
        lines.append("---")
    return "\n".join(lines)


@with_retry(max_attempts=3, backoff=1.5)
async def _tavily_search(query: str, max_results: int = 5) -> list[dict]:
    """Raw Tavily call — wrapped with retry decorator."""
    # Tavily is synchronous, run it in a thread pool so we don't block async
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: _client.search(query, max_results=max_results)
    )
    return result.get("results", [])


@tool
async def search_web(query: str) -> str:
    """
    Search the web for general information about a company.
    Use this for: company overview, what they do, their products, funding history,
    team size, founding year, or any general background information.
    Do NOT use this for recent news — use search_recent_news for that.
    """
    if _tavily_cb.is_open():
        logger.warning("tool_skipped_circuit_open", tool="search_web")
        return "Web search unavailable — circuit breaker open. Try other tools."

    start = time.time()
    try:
        results = await asyncio.wait_for(
            _tavily_search(query),
            timeout=settings.tavily_timeout_s
        )
        duration_ms = round((time.time() - start) * 1000)
        logger.info("tool_call", tool="search_web", query=query[:60],
                    results_count=len(results), duration_ms=duration_ms)
        _tavily_cb.record_success()
        return _format_results(results)

    except asyncio.TimeoutError:
        _tavily_cb.record_failure()
        logger.error("tool_timeout", tool="search_web", timeout_s=settings.tavily_timeout_s)
        return f"Web search timed out after {settings.tavily_timeout_s}s."

    except Exception as e:
        _tavily_cb.record_failure()
        logger.error("tool_failed", tool="search_web", error=str(e)[:100])
        return f"Web search failed: {str(e)[:100]}"


@tool
async def search_recent_news(company: str) -> str:
    """
    Search for recent news, announcements, product launches, and funding rounds
    from the last 90 days for a specific company.
    Use this to find: new features, partnerships, hires, press releases,
    funding rounds, acquisitions, or any recent events about the company.
    Always call this — recent context is critical for sales conversations.
    """
    if _tavily_cb.is_open():
        logger.warning("tool_skipped_circuit_open", tool="search_recent_news")
        return "News search unavailable — circuit breaker open."

    # Add year context to bias results towards recent content
    query = f"{company} news announcement launch funding 2025 2026"

    start = time.time()
    try:
        results = await asyncio.wait_for(
            _tavily_search(query, max_results=5),
            timeout=settings.tavily_timeout_s
        )
        duration_ms = round((time.time() - start) * 1000)
        logger.info("tool_call", tool="search_recent_news", company=company,
                    results_count=len(results), duration_ms=duration_ms)
        _tavily_cb.record_success()
        return _format_results(results)

    except asyncio.TimeoutError:
        _tavily_cb.record_failure()
        logger.error("tool_timeout", tool="search_recent_news")
        return f"News search timed out."

    except Exception as e:
        _tavily_cb.record_failure()
        logger.error("tool_failed", tool="search_recent_news", error=str(e)[:100])
        return f"News search failed: {str(e)[:100]}"
