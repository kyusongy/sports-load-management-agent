"""
Visualization Node for the sports load management workflow.

Generates default set of charts for the processed data.
"""

from typing import Any, Dict

from loguru import logger

from sports_load_agent.agent_state import AgentState
from sports_load_agent.core.visualizations import LoadVisualizer
from sports_load_agent.settings import OUTPUTS_DIR


def visualization_node(state: AgentState) -> Dict[str, Any]:
    """
    Visualization node that generates charts from processed data.

    Workflow:
    1. Load processed data from DataFrameHandle
    2. Generate default visualization set:
       - Top 5 players by load (bar chart)
       - Load quality distribution (pie chart)
       - Team load timeline
       - Player load heatmap
       - Top 5 players by training load
    3. Save plots to output directory

    Args:
        state: Current agent state with processed_data.

    Returns:
        State updates with visualization_files list.
    """
    logger.info("=== Visualization Node ===")

    processed_data = state.get("processed_data")
    session_id = state.get("session_id", "unknown")

    if processed_data is None:
        logger.error("No processed data available")
        return {
            "status": "failed",
            "current_stage": "visualization",
            "error_message": "No processed data available for visualization",
        }

    try:
        # Load the DataFrame
        df = processed_data.load(format="pandas")
        logger.info(f"Loaded processed data for visualization: {df.shape}")

        # Generate visualizations
        visualizer = LoadVisualizer(df, OUTPUTS_DIR)
        plot_files = visualizer.generate_default_set(session_id)

        logger.info(f"Generated {len(plot_files)} visualizations")

        return {
            "visualization_files": plot_files,
            "status": "processing",
            "current_stage": "visualization",
            "error_message": None,
        }

    except Exception as e:
        logger.exception(f"Visualization generation failed: {e}")
        return {
            "status": "failed",
            "current_stage": "visualization",
            "error_message": f"Visualization error: {str(e)}",
        }


__all__ = ["visualization_node"]

