from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from meetiq.agents.nodes import TOOLS, agent_node, synthesize_node
from meetiq.agents.state import ResearchState
from meetiq.core.logging import logger


def should_continue(state: ResearchState) -> str:
    """
    The router function — called after every agent_node run.

    Looks at the last message from the agent:
    - If it has tool_calls → agent wants to call tools → go to "tools"
    - If no tool_calls   → agent is done researching  → go to "synthesize"

    This is the conditional edge that creates the ReAct loop.
    """
    last_message = state["messages"][-1]

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        logger.info("routing_to_tools",
                    tools_requested=[tc["name"] for tc in last_message.tool_calls])
        return "tools"

    logger.info("routing_to_synthesize")
    return "synthesize"


def build_research_graph():
    """
    Build and compile the LangGraph research agent.

    Graph structure:
        START → agent → (conditional) → tools → agent  (loop)
                                      → synthesize → END
    """
    graph = StateGraph(ResearchState)

    # ── Add nodes ─────────────────────────────────────────────────────────
    graph.add_node("agent", agent_node)

    # ToolNode is a LangGraph built-in: reads tool_calls from the last AIMessage,
    # executes each tool, and returns ToolMessages with results.
    # It handles async tools, parallel tool calls, and errors automatically.
    graph.add_node("tools", ToolNode(TOOLS))

    graph.add_node("synthesize", synthesize_node)

    # ── Add edges ─────────────────────────────────────────────────────────
    graph.add_edge(START, "agent")   # always start with the agent

    # Conditional edge: agent → tools or synthesize depending on should_continue()
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",         # if tool_calls present → execute tools
            "synthesize": "synthesize",  # if no tool_calls → done
        }
    )

    graph.add_edge("tools", "agent")     # after tools run → back to agent
    graph.add_edge("synthesize", END)    # after synthesis → done

    # recursion_limit caps total node executions in one run.
    # Each tool call = 2 nodes (agent → tool). Cap at 16 = ~6 tool calls max.
    # Without this, Gemini will keep calling tools and exhaust the daily quota.
    return graph.compile()


# Single compiled graph instance — imported by research_service
research_graph = build_research_graph()

# Default invoke config: cap iterations, expose for override in research_service
GRAPH_CONFIG = {"recursion_limit": 16}
