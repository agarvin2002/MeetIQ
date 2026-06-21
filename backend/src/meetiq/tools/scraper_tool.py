import asyncio
import time

import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool

from meetiq.config.settings import settings
from meetiq.core.logging import logger

# Pretend to be a browser so sites don't block us
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def _extract_text(html: str, max_chars: int = 3000) -> str:
    """
    Extract clean readable text from HTML.
    Pulls: title, meta description, h1/h2 headings, and main body text.
    Strips: scripts, styles, nav, footer (boilerplate).
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove noise
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    parts = []

    # Page title
    if soup.title:
        parts.append(f"Title: {soup.title.string}")

    # Meta description (often the clearest company description)
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        parts.append(f"Description: {meta_desc['content']}")

    # Main headings
    for tag in soup.find_all(["h1", "h2"])[:5]:
        text = tag.get_text(strip=True)
        if text:
            parts.append(f"Heading: {text}")

    # Body text (first meaningful paragraphs)
    for p in soup.find_all("p")[:15]:
        text = p.get_text(strip=True)
        if len(text) > 40:  # skip tiny fragments
            parts.append(text)

    result = "\n".join(parts)
    return result[:max_chars]


@tool
async def scrape_homepage(domain: str) -> str:
    """
    Scrape the company's website homepage to extract their description,
    product offering, mission, and any visible technology mentions.
    Use this when you have the company's domain name.
    Good for: understanding what the company does in their own words.
    Input should be just the domain, e.g. 'linear.app' or 'stripe.com'.
    """
    start = time.time()

    # Try https first, fall back to http
    for scheme in ["https", "http"]:
        url = f"{scheme}://{domain}"
        try:
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda u=url: requests.get(u, headers=HEADERS, timeout=settings.scraper_timeout_s)
                ),
                timeout=settings.scraper_timeout_s + 2
            )

            if response.status_code == 200:
                text = _extract_text(response.text)
                duration_ms = round((time.time() - start) * 1000)
                logger.info("tool_call", tool="scrape_homepage", domain=domain,
                            chars=len(text), duration_ms=duration_ms)
                return f"Homepage content from {url}:\n\n{text}"

        except asyncio.TimeoutError:
            logger.warning("tool_timeout", tool="scrape_homepage", url=url)
            continue
        except Exception as e:
            logger.warning("tool_scrape_error", url=url, error=str(e)[:80])
            continue

    return f"Could not scrape {domain} — site may be blocking requests or unreachable."
