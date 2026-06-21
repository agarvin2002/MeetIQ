from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class ResearchState(TypedDict):
    """
    The shared state that flows through every node in the research graph.

    LangGraph passes this dict from node to node. Each node receives the
    current state and returns a partial update (only the keys it changed).

    The 'messages' field uses add_messages — a special LangGraph annotation
    that APPENDS new messages to the list instead of replacing it.
    This gives the agent its full conversation history.
    """

    # Full conversation: HumanMessage → AIMessage (with tool calls) → ToolMessage → ...
    # add_messages means: when agent returns {"messages": [new_msg]},
    # LangGraph appends new_msg to the existing list instead of replacing it
    messages: Annotated[list, add_messages]

    # Input context — set once at the start, never changed
    company_name: str
    domain: str | None   # May be None if we only have company name, not domain

    # Populated at the end by synthesize_node
    brief: dict | None
