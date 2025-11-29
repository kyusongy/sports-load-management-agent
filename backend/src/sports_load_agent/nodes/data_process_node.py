"""
Data Processing Node for the sports load management workflow.

Applies LoadCalculator to compute ACWR metrics and categorize load quality.
"""

from typing import Any, Dict

from loguru import logger

from sports_load_agent.agent_state import AgentState, DataFrameHandle
from sports_load_agent.core.load_calculator import LoadCalculator
from sports_load_agent.settings import OUTPUTS_DIR


def data_process_node(state: AgentState) -> Dict[str, Any]:
    """
    Data processing node that calculates load metrics.

    Workflow:
    1. Load raw data from DataFrameHandle
    2. Apply LoadCalculator:
       - Clean data (handle missing values)
       - Compute short-term average (3-day)
       - Compute long-term average (2-week)
       - Calculate ACWR (load = short/long)
       - Categorize load quality
    3. Save processed CSV and Excel files
    4. Store processed data as DataFrameHandle

    Args:
        state: Current agent state with raw_data.

    Returns:
        State updates with processed_data and file paths.
    """
    logger.info("=== Data Processing Node ===")

    raw_data = state.get("raw_data")
    session_id = state.get("session_id", "unknown")

    if raw_data is None:
        logger.error("No raw data available")
        return {
            "status": "failed",
            "current_stage": "data_process",
            "error_message": "No raw data available for processing",
        }

    try:
        # Load the DataFrame
        df = raw_data.load(format="pandas")
        logger.info(f"Loaded raw data: {df.shape}")

        # Apply LoadCalculator
        calculator = LoadCalculator(df)
        calculator.process_all()

        processed_df = calculator.get_result()
        stats = calculator.get_summary_stats()

        logger.info(f"Processing complete. Stats: {stats}")

        # Save processed files
        csv_path = OUTPUTS_DIR / f"{session_id}_processed.csv"
        excel_path = OUTPUTS_DIR / f"{session_id}_processed.xlsx"

        calculator.save_processed_data(
            csv_path=str(csv_path),
            excel_path=str(excel_path),
        )

        # Create DataFrameHandle for processed data
        processed_handle = DataFrameHandle(
            dataframe=processed_df,
            sources=raw_data.sources,
            processing_fingerprints=raw_data.processing_fingerprints
            + ["clean", "short_term_ave", "long_term_ave", "load_quality"],
        )

        return {
            "processed_data": processed_handle,
            "processed_csv_path": str(csv_path),
            "processed_excel_path": str(excel_path),
            "status": "completed",  # Final node - ready for chat interaction
            "current_stage": "data_process",
            "error_message": None,
        }

    except Exception as e:
        logger.exception(f"Data processing failed: {e}")
        return {
            "status": "failed",
            "current_stage": "data_process",
            "error_message": f"Data processing error: {str(e)}",
        }


__all__ = ["data_process_node"]

