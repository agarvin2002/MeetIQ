from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage, SystemMessage

from meetiq.agents.state import ResearchState
from meetiq.config.settings import settings
from meetiq.core.logging import logger
from meetiq.tools.jobs_tool import search_job_listings
from meetiq.tools.scraper_tool import scrape_homepage
from meetiq.tools.tavily_tool import search_recent_news, search_web

# All tools the agent can call — Claude reads docstrings to pick the right one
TOOLS = [search_web, search_recent_news, scrape_homepage, search_job_listings]

def _make_llm(temperature: float = 0.1):
    """Build a ChatBedrockConverse instance with credentials from settings."""
    return ChatBedrockConverse(
        model=settings.bedrock_model,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region,
        temperature=temperature,
    )

# The LLM that drives the research loop — has tools bound so it can call them
_research_llm = _make_llm(temperature=0.1).bind_tools(TOOLS)

# Separate LLM for synthesis — no tools, just structured JSON output
_synthesis_llm = _make_llm(temperature=0.2)

# System prompt: sets the agent's persona and research goal
SYSTEM_PROMPT = """You are a sales intelligence researcher preparing a pre-meeting brief.

Your job: Research {company_name}{domain_hint} thoroughly before a sales call.

Gather this information using the available tools:
1. What the company does — plain language, not marketing copy
2. Recent news, funding, product launches from the LAST 90 DAYS ONLY
3. Tech stack signals — what tools, languages, frameworks they use
4. Inferred pain points based on their stage and public activity

Rules:
- Use AT LEAST 2 different tools, AT MOST 4 tools before finishing
- Do NOT invent information not found in your searches
- If a tool fails, try a different one
- STOP after 4 tool calls even if you want more data
- When you have enough information, stop calling tools and return your final answer

Start researching now."""

SYNTHESIS_PROMPT = """Based on the research below, create a structured intelligence brief.

Company: {company_name}

Research collected:
{research_content}

Return a JSON object with exactly these fields:
{{
  "description": "2-3 sentences: what the company does in plain language",
  "recent_news": ["news item 1", "news item 2", "news item 3"],
  "tech_signals": ["signal 1", "signal 2", "signal 3"],
  "pain_points": ["pain point 1", "pain point 2"],
  "talking_points": ["talking point 1", "talking point 2", "talking point 3"],
  "sources_used": ["source url 1", "source url 2"]
}}

Rules:
- recent_news: only events from last 90 days. If none found, use empty list.
- tech_signals: specific tools/languages/frameworks found in research
- talking_points: exactly 2-3 specific, non-generic conversation starters
- Do NOT make up numbers, revenue, or headcount not found in research
- Return ONLY valid JSON, no explanation text"""


async def agent_node(state: ResearchState) -> dict:
    """
    The research agent node.

    On first call: builds system prompt + human message, saves both to state,
                   then calls Gemini with the full message list.
    On subsequent calls: state already has the full history — just invoke with it.

    Gemini responds with either:
    - tool_calls → wants to call one of our tools (graph routes to tool_node)
    - regular text → done researching (graph routes to synthesize_node)
    """
    messages = state["messages"]
    new_messages = []

    # First call: build and SAVE the initial context to state
    if not messages:
        domain_hint = f" ({state['domain']})" if state.get("domain") else ""
        system = SystemMessage(content=SYSTEM_PROMPT.format(
            company_name=state["company_name"],
            domain_hint=domain_hint,
        ))
        human = HumanMessage(content=f"Research {state['company_name']} for an upcoming sales meeting.")
        new_messages = [system, human]
        messages = new_messages  # use these for this invocation

    logger.info("agent_node_called",
                company=state["company_name"],
                message_count=len(messages))

    response = await _research_llm.ainvoke(messages)

    # Always return ALL new messages so state is complete
    # new_messages is [system, human] on first call, [] on subsequent calls
    return {"messages": new_messages + [response]}


async def synthesize_node(state: ResearchState) -> dict:
    """
    Called once when the agent stops calling tools.

    Extracts all tool results from message history and asks Gemini
    to synthesize them into a structured JSON brief.
    """
    import json
    import re

    # Collect all tool result messages from history
    research_parts = []
    sources = []
    for msg in state["messages"]:
        # ToolMessage = result of a tool call
        if hasattr(msg, "content") and hasattr(msg, "tool_call_id"):
            research_parts.append(msg.content)
        # Extract URLs for source attribution
        urls = re.findall(r'Source: (https?://\S+)', msg.content if hasattr(msg, "content") and isinstance(msg.content, str) else "")
        sources.extend(urls[:2])

    research_content = "\n\n---\n\n".join(research_parts) if research_parts else "Limited research available."

    logger.info("synthesize_node_called",
                company=state["company_name"],
                research_chunks=len(research_parts))

    prompt = SYNTHESIS_PROMPT.format(
        company_name=state["company_name"],
        research_content=research_content[:8000],  # token budget guard
    )

    response = await _synthesis_llm.ainvoke([HumanMessage(content=prompt)])

    # Parse JSON from response — clean up markdown code blocks if present
    raw = response.content.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        brief_dict = json.loads(raw)
        # Add sources we tracked
        if sources:
            brief_dict.setdefault("sources_used", sources)
        logger.info("synthesis_complete", company=state["company_name"])
    except json.JSONDecodeError as e:
        logger.error("synthesis_json_error", error=str(e), raw=raw[:200])
        # Fallback: return a minimal valid brief
        brief_dict = {
            "description": f"Research gathered for {state['company_name']}. Manual review needed.",
            "recent_news": [],
            "tech_signals": [],
            "pain_points": [],
            "talking_points": ["Ask about their current challenges", "Discuss their growth plans"],
            "sources_used": sources,
        }

    return {"brief": brief_dict}
