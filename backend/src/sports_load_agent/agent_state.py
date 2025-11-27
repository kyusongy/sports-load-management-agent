"""
Agent state schema for sports load management workflow.

Provides DataFrameHandle for efficient DataFrame serialization and AgentState
for tracking the workflow state through the LangGraph pipeline.
"""

import hashlib
import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, TypedDict, Union

import pandas as pd
import polars as pl
import pyarrow.feather as feather

from sports_load_agent.settings import RUNTIME_CACHE_DIR


DEFAULT_CACHE_DIR = RUNTIME_CACHE_DIR / "dataframes"
DEFAULT_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class DataFrameHandle:
    """
    A serializable handle for a Pandas or Polars DataFrame.

    Stores metadata and a path to the DataFrame cached on disk in Apache Arrow
    Feather format. Allows passing through LangGraph serialization with data
    loaded only when explicitly requested.
    """

    def __init__(
        self,
        dataframe: Union[pd.DataFrame, pl.DataFrame, pl.LazyFrame],
        sources: List[str],
        processing_fingerprints: List[str],
        *,
        cache_dir: Union[str, Path] = DEFAULT_CACHE_DIR,
    ):
        """
        Initialize the handle, save DataFrame to cache, and store metadata.

        Args:
            dataframe: The DataFrame to manage.
            sources: List of data sources for this data.
            processing_fingerprints: Fingerprints of processing steps.
            cache_dir: Base directory for caching DataFrame files.
        """
        self.sources = sorted(sources)
        self.processing_fingerprints = processing_fingerprints
        self._cache_dir = Path(cache_dir)
        self.df_type: str = "pandas"

        # Determine DataFrame type and get concrete DataFrame
        concrete_df: Any
        if isinstance(dataframe, pd.DataFrame):
            self.df_type = "pandas"
            concrete_df = dataframe
        elif isinstance(dataframe, pl.LazyFrame):
            self.df_type = "polars"
            concrete_df = dataframe.collect()
        elif isinstance(dataframe, pl.DataFrame):
            self.df_type = "polars"
            concrete_df = dataframe
        else:
            raise TypeError(
                f"Unsupported dataframe type: {type(dataframe)}. "
                "Must be pd.DataFrame, pl.DataFrame, or pl.LazyFrame."
            )

        # Generate UID and paths
        self.uid = self._generate_uid()
        self._cache_path = self._cache_dir / f"{self.uid}.arrow"

        # Metadata attributes
        self.shape: Optional[Tuple[int, int]] = None
        self.columns: Optional[List[str]] = None
        self.metadata: Dict[str, Any] = {}

        # Save and populate metadata
        self._save(concrete_df)

    def _generate_uid(self) -> str:
        """Create unique SHA256 hash based on sources and processing steps."""
        hasher = hashlib.sha256()
        for source in self.sources:
            hasher.update(source.encode("utf-8"))
        for fingerprint in self.processing_fingerprints:
            hasher.update(fingerprint.encode("utf-8"))
        return hasher.hexdigest()

    def _save(self, dataframe: Union[pd.DataFrame, Any]) -> None:
        """Save DataFrame to cache using Feather format."""
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        if self.df_type == "polars":
            data_to_save = dataframe.to_arrow()
        else:
            data_to_save = dataframe

        feather.write_feather(data_to_save, self._cache_path)

        self.shape = dataframe.shape
        self.columns = (
            dataframe.columns
            if self.df_type == "polars"
            else dataframe.columns.tolist()
        )

    def load(self, format: Optional[str] = "pandas") -> Union[pd.DataFrame, Any]:
        """
        Load DataFrame from cache into memory.

        Args:
            format: Desired output format ('pandas', 'polars', or 'polars_lazy').

        Returns:
            The loaded DataFrame in the requested format.
        """
        if not self._cache_path.exists():
            raise FileNotFoundError(
                f"Cache file not found for UID {self.uid} at {self._cache_path}"
            )

        output_format = format if format else self.df_type
        valid_formats = ["pandas", "polars", "polars_lazy"]

        if output_format not in valid_formats:
            raise ValueError(f"Format must be one of {valid_formats}.")

        if output_format == "pandas":
            return feather.read_feather(self._cache_path)
        elif output_format.startswith("polars"):
            polars_df = pl.read_ipc(self._cache_path)
            if output_format == "polars_lazy":
                return polars_df.lazy()
            return polars_df

    def __repr__(self) -> str:
        return (
            f"DataFrameHandle(uid='{self.uid[:12]}...', type='{self.df_type}', "
            f"shape={self.shape}, sources={len(self.sources)})"
        )

    def __getstate__(self) -> Dict[str, Any]:
        """Serialize for pickling/msgpack."""
        return {
            "uid": self.uid,
            "df_type": self.df_type,
            "sources": self.sources,
            "processing_fingerprints": self.processing_fingerprints,
            "shape": self.shape,
            "columns": self.columns,
            "cache_dir": str(self._cache_dir),
        }

    def __setstate__(self, state: Dict[str, Any]) -> None:
        """Deserialize from pickling/msgpack."""
        self.uid = state["uid"]
        self.df_type = state["df_type"]
        self.sources = state["sources"]
        self.processing_fingerprints = state["processing_fingerprints"]
        self.shape = state["shape"]
        self.columns = state["columns"]
        self._cache_dir = Path(state["cache_dir"])
        self._cache_path = self._cache_dir / f"{self.uid}.arrow"
        self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.__getstate__()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DataFrameHandle":
        """Create DataFrameHandle from dictionary."""
        instance = cls.__new__(cls)
        instance.__setstate__(data)
        return instance


# Processing status types
ProcessingStatus = Literal["pending", "processing", "completed", "failed"]


class AgentState(TypedDict, total=False):
    """
    Agent state for sports load management workflow.

    Tracks data through the pipeline: ingest -> process -> visualize -> report
    """

    # Session identification
    session_id: str

    # Input data
    uploaded_files: List[str]  # Paths to uploaded CSV files
    raw_data: Optional[DataFrameHandle]  # Combined raw data after ingestion

    # Column mapping results
    column_mapping: Dict[str, str]  # Original -> standardized column names
    has_srpe_columns: bool  # True if RPE and Time columns exist (need multiplication)

    # Processed data
    processed_data: Optional[DataFrameHandle]  # After LoadCalculator processing

    # Visualization outputs
    visualization_files: List[str]  # Paths to generated plot files

    # Report outputs
    report_markdown: Optional[str]  # LLM-generated report
    processed_csv_path: Optional[str]  # Path to processed CSV
    processed_excel_path: Optional[str]  # Path to colored Excel

    # Processing status
    status: ProcessingStatus
    current_stage: Optional[str]  # Current node name
    error_message: Optional[str]  # Error details if failed

    # Token tracking
    token_usage: Dict[str, int]  # Token usage statistics


def create_initial_state(session_id: str, uploaded_files: List[str]) -> AgentState:
    """
    Create initial agent state for a new processing session.

    Args:
        session_id: Unique session identifier.
        uploaded_files: List of uploaded file paths.

    Returns:
        Initialized AgentState.
    """
    return AgentState(
        session_id=session_id,
        uploaded_files=uploaded_files,
        raw_data=None,
        column_mapping={},
        has_srpe_columns=False,
        processed_data=None,
        visualization_files=[],
        report_markdown=None,
        processed_csv_path=None,
        processed_excel_path=None,
        status="pending",
        current_stage=None,
        error_message=None,
        token_usage={},
    )


__all__ = [
    "DataFrameHandle",
    "AgentState",
    "ProcessingStatus",
    "create_initial_state",
]

