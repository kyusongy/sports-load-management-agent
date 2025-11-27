"""
Data Ingestion Node for the sports load management workflow.

Handles file loading, column detection, mapping, and standardization.
"""

from typing import Any, Dict

import pandas as pd
from loguru import logger

from sports_load_agent.agent_state import AgentState, DataFrameHandle
from sports_load_agent.utils.column_mapper import ColumnMapper, combine_multiple_files


def data_ingest_node(state: AgentState) -> Dict[str, Any]:
    """
    Data ingestion node that loads and standardizes uploaded files.

    Workflow:
    1. Load uploaded CSV files
    2. Detect and map columns to standardized format
    3. Calculate sRPE (RPE × Time) if needed
    4. Combine multiple files if present
    5. Store raw data as DataFrameHandle

    Args:
        state: Current agent state with uploaded_files.

    Returns:
        State updates with raw_data and column_mapping.
    """
    logger.info("=== Data Ingestion Node ===")

    uploaded_files = state.get("uploaded_files", [])
    session_id = state.get("session_id", "unknown")

    if not uploaded_files:
        logger.error("No files uploaded")
        return {
            "status": "failed",
            "current_stage": "data_ingest",
            "error_message": "No files uploaded for processing",
        }

    try:
        logger.info(f"Processing {len(uploaded_files)} file(s)")

        if len(uploaded_files) == 1:
            # Single file processing
            df = pd.read_csv(uploaded_files[0])
            mapper = ColumnMapper(df)
            mapper.detect_columns()
            standardized_df = mapper.apply_mapping()
            mapping_report = mapper.get_mapping_report()
            has_srpe = mapper.has_srpe_columns
        else:
            # Multiple files - combine them
            standardized_df, reports = combine_multiple_files(uploaded_files)
            mapping_report = {"files": reports}
            # Check if any file used sRPE
            has_srpe = any(r.get("has_srpe_columns", False) for r in reports if "error" not in r)

        if standardized_df.empty:
            logger.error("No data after processing")
            return {
                "status": "failed",
                "current_stage": "data_ingest",
                "error_message": "No valid data found in uploaded files",
            }

        # Validate required columns
        required_cols = {"player_name", "date", "data"}
        if not required_cols.issubset(set(standardized_df.columns)):
            missing = required_cols - set(standardized_df.columns)
            logger.error(f"Missing required columns: {missing}")
            return {
                "status": "failed",
                "current_stage": "data_ingest",
                "error_message": f"Missing required columns: {missing}. Please ensure your data has player identifier, date, and load (or RPE + Time) columns.",
            }

        # Create DataFrameHandle for the raw data
        raw_handle = DataFrameHandle(
            dataframe=standardized_df,
            sources=uploaded_files,
            processing_fingerprints=["ingest", "column_mapping"],
        )

        logger.info(
            f"Ingestion complete: {raw_handle.shape[0]} rows, "
            f"{standardized_df['player_name'].nunique()} players"
        )

        return {
            "raw_data": raw_handle,
            "column_mapping": mapping_report,
            "has_srpe_columns": has_srpe,
            "status": "processing",
            "current_stage": "data_ingest",
            "error_message": None,
        }

    except Exception as e:
        logger.exception(f"Data ingestion failed: {e}")
        return {
            "status": "failed",
            "current_stage": "data_ingest",
            "error_message": f"Data ingestion error: {str(e)}",
        }


__all__ = ["data_ingest_node"]

