"""
LangGraph workflow definition for sports load management.

Defines the graph structure: data_ingest -> data_process -> visualization -> report_generation
"""

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from loguru import logger

from sports_load_agent.agent_state import AgentState
from sports_load_agent.nodes import (
    data_ingest_node,
    data_process_node,
    report_generation_node,
    visualization_node,
)


def _routing_after_ingest(state: AgentState) -> Literal["data_process", "END"]:
    """Route after data ingestion based on status."""
    if state.get("status") == "failed":
        logger.warning("Routing to END due to ingestion failure")
        return "END"
    return "data_process"


def _routing_after_process(state: AgentState) -> Literal["visualization", "END"]:
    """Route after data processing based on status."""
    if state.get("status") == "failed":
        logger.warning("Routing to END due to processing failure")
        return "END"
    return "visualization"


def _routing_after_visualization(state: AgentState) -> Literal["report_generation", "END"]:
    """Route after visualization based on status."""
    if state.get("status") == "failed":
        logger.warning("Routing to END due to visualization failure")
        return "END"
    return "report_generation"


def _build_workflow() -> StateGraph:
    """
    Build the sports load management workflow graph.

    Flow: START -> data_ingest -> data_process -> visualization -> report_generation -> END
    """
    logger.info("Building sports load management workflow...")

    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("data_ingest", data_ingest_node)
    workflow.add_node("data_process", data_process_node)
    workflow.add_node("visualization", visualization_node)
    workflow.add_node("report_generation", report_generation_node)

    # Entry point
    workflow.add_edge(START, "data_ingest")

    # Conditional routing with error handling
    workflow.add_conditional_edges(
        "data_ingest",
        _routing_after_ingest,
        {
            "data_process": "data_process",
            "END": END,
        },
    )

    workflow.add_conditional_edges(
        "data_process",
        _routing_after_process,
        {
            "visualization": "visualization",
            "END": END,
        },
    )

    workflow.add_conditional_edges(
        "visualization",
        _routing_after_visualization,
        {
            "report_generation": "report_generation",
            "END": END,
        },
    )

    # Final edge
    workflow.add_edge("report_generation", END)

    logger.info("Workflow built successfully")
    return workflow


# Build the workflow at module load
_WORKFLOW = _build_workflow()


def create_graph(session_id: str) -> Any:
    """
    Create a compiled graph.

    For single-pass workflows, we don't need checkpointing.
    The graph runs from start to end in one invocation.

    Args:
        session_id: Unique session identifier.

    Returns:
        Compiled graph ready for execution.
    """
    # For single-pass workflow, compile without checkpointer
    # This avoids serialization issues with DataFrameHandle
    graph = _WORKFLOW.compile()

    logger.info(f"Graph compiled for session {session_id}")
    return graph


def create_graph_without_checkpointer() -> Any:
    """
    Create a compiled graph without checkpointing (for simple runs).

    Returns:
        Compiled graph.
    """
    return _WORKFLOW.compile()


# Export for langgraph.json
graph = create_graph_without_checkpointer()


__all__ = ["create_graph", "create_graph_without_checkpointer", "graph"]

