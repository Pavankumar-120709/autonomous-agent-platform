import logging
from langgraph.graph import StateGraph, START, END
from .state import AgentGraphState
from .planner import plan_node
from .executor import execute_tool_node
from .observer import observe_node
from .decider import decide_node
from .finalizer import finalize_node

logger = logging.getLogger("agent.graph")


def route_after_plan(state: AgentGraphState) -> str:
    if state.get("decision") == "STOP_LIMIT":
        return "finalize"
    return "execute_tool"


def route_after_execute(state: AgentGraphState) -> str:
    if state.get("decision") == "STOP_LIMIT":
        return "finalize"
    return "observe"


def route_after_observe(state: AgentGraphState) -> str:
    if state.get("decision") == "STOP_LIMIT":
        return "finalize"
    return "decide"


def route_after_decide(state: AgentGraphState) -> str:
    if state.get("decision") == "EXECUTE_TOOL":
        return "execute_tool"
    return "finalize"


def build_agent_graph() -> StateGraph:
    """
    Constructs the bounded LangGraph state machine:
    START -> PLAN -> EXECUTE_TOOL -> OBSERVE -> DECIDE -> (EXECUTE_TOOL | FINALIZE) -> END
    """
    builder = StateGraph(AgentGraphState)

    # Register nodes
    builder.add_node("plan", plan_node)
    builder.add_node("execute_tool", execute_tool_node)
    builder.add_node("observe", observe_node)
    builder.add_node("decide", decide_node)
    builder.add_node("finalize", finalize_node)

    # Edges & conditional transitions
    builder.add_edge(START, "plan")

    builder.add_conditional_edges(
        "plan",
        route_after_plan,
        {
            "execute_tool": "execute_tool",
            "finalize": "finalize",
        },
    )

    builder.add_conditional_edges(
        "execute_tool",
        route_after_execute,
        {
            "observe": "observe",
            "finalize": "finalize",
        },
    )

    builder.add_conditional_edges(
        "observe",
        route_after_observe,
        {
            "decide": "decide",
            "finalize": "finalize",
        },
    )

    builder.add_conditional_edges(
        "decide",
        route_after_decide,
        {
            "execute_tool": "execute_tool",
            "finalize": "finalize",
        },
    )

    builder.add_edge("finalize", END)

    return builder.compile()


agent_app = build_agent_graph()
