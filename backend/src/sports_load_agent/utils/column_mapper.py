"""
Column Mapper for automatic column detection and standardization.

Detects player identifier, date, and load columns (or RPE + Time for sRPE calculation).
Uses fuzzy matching to handle various naming conventions.
"""

import re
from typing import Dict, List, Optional, Tuple

import pandas as pd
from loguru import logger


class ColumnMapper:
    """
    Smart column detection and mapping for training load data.

    Identifies and standardizes columns to: player_name, date, data
    """

    # Column patterns for detection (case-insensitive)
    PLAYER_PATTERNS = [
        r"^athlete[\s_]?name$",
        r"^player[\s_]?name$",
        r"^player$",
        r"^athlete$",
        r"^name$",
        r"^player[\s_]?id$",
        r"^athlete[\s_]?id$",
        r"^id$",
    ]

    DATE_PATTERNS = [
        r"^date$",
        r"^day$",
        r"^training[\s_]?date$",
        r"^session[\s_]?date$",
    ]

    LOAD_PATTERNS = [
        r"^load$",
        r"^training[\s_]?load$",
        r"^srpe$",
        r"^session[\s_]?load$",
        r"^workload$",
        r"^data$",
    ]

    RPE_PATTERNS = [
        r"^rpe$",
        r"^rating[\s_]?of[\s_]?perceived[\s_]?exertion$",
        r"^perceived[\s_]?exertion$",
    ]

    TIME_PATTERNS = [
        r"^time$",
        r"^time[\s_]?\(?mins?\)?$",
        r"^duration$",
        r"^duration[\s_]?\(?mins?\)?$",
        r"^minutes$",
        r"^session[\s_]?time$",
        r"^training[\s_]?time$",
    ]

    def __init__(self, df: pd.DataFrame):
        """
        Initialize with a DataFrame.

        Args:
            df: Raw DataFrame to analyze.
        """
        self.df = df
        self.original_columns = list(df.columns)
        self.mapping: Dict[str, str] = {}
        self.has_srpe_columns = False
        self.rpe_column: Optional[str] = None
        self.time_column: Optional[str] = None

    def _match_column(self, patterns: List[str]) -> Optional[str]:
        """
        Find first column matching any of the patterns.

        Args:
            patterns: List of regex patterns to match.

        Returns:
            Matched column name or None.
        """
        for col in self.original_columns:
            col_lower = col.lower().strip()
            for pattern in patterns:
                if re.match(pattern, col_lower):
                    return col
        return None

    def detect_columns(self) -> Dict[str, str]:
        """
        Detect and map columns to standardized names.

        Returns:
            Dictionary mapping original column names to standardized names.
        """
        # Detect player column
        player_col = self._match_column(self.PLAYER_PATTERNS)
        if player_col:
            self.mapping[player_col] = "player_name"
            logger.info(f"Detected player column: '{player_col}' -> 'player_name'")
        else:
            logger.warning("Could not detect player identifier column")

        # Detect date column
        date_col = self._match_column(self.DATE_PATTERNS)
        if date_col:
            self.mapping[date_col] = "date"
            logger.info(f"Detected date column: '{date_col}' -> 'date'")
        else:
            logger.warning("Could not detect date column")

        # Detect load column OR RPE + Time columns
        load_col = self._match_column(self.LOAD_PATTERNS)
        if load_col:
            self.mapping[load_col] = "data"
            logger.info(f"Detected load column: '{load_col}' -> 'data'")
        else:
            # Try to find RPE and Time for sRPE calculation
            rpe_col = self._match_column(self.RPE_PATTERNS)
            time_col = self._match_column(self.TIME_PATTERNS)

            if rpe_col and time_col:
                self.has_srpe_columns = True
                self.rpe_column = rpe_col
                self.time_column = time_col
                logger.info(
                    f"Detected sRPE columns: RPE='{rpe_col}', Time='{time_col}' "
                    "-> will calculate 'data' = RPE × Time"
                )
            else:
                logger.warning(
                    "Could not detect load column or RPE/Time columns for sRPE calculation"
                )

        return self.mapping

    def apply_mapping(self) -> pd.DataFrame:
        """
        Apply column mapping and calculate sRPE if needed.

        Returns:
            Standardized DataFrame with columns: player_name, date, data
        """
        result_df = self.df.copy()

        # Rename mapped columns
        if self.mapping:
            result_df = result_df.rename(columns=self.mapping)

        # Calculate sRPE if we have RPE and Time columns
        if self.has_srpe_columns and self.rpe_column and self.time_column:
            # Convert to numeric, coercing errors to NaN
            rpe_values = pd.to_numeric(result_df[self.rpe_column], errors="coerce")
            time_values = pd.to_numeric(result_df[self.time_column], errors="coerce")

            # Calculate sRPE = RPE × Time
            result_df["data"] = rpe_values * time_values
            logger.info(f"Calculated sRPE (data) = {self.rpe_column} × {self.time_column}")

        # Select only standardized columns
        required_cols = ["player_name", "date", "data"]
        available_cols = [col for col in required_cols if col in result_df.columns]

        if len(available_cols) < 3:
            missing = set(required_cols) - set(available_cols)
            logger.error(f"Missing required columns after mapping: {missing}")

        return result_df[available_cols]

    def get_mapping_report(self) -> Dict:
        """
        Get a report of the column mapping results.

        Returns:
            Dictionary with mapping details.
        """
        return {
            "original_columns": self.original_columns,
            "mapping": self.mapping,
            "has_srpe_columns": self.has_srpe_columns,
            "rpe_column": self.rpe_column,
            "time_column": self.time_column,
            "standardized_columns": ["player_name", "date", "data"],
        }


def combine_multiple_files(file_paths: List[str]) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    Combine multiple CSV files into a single DataFrame.

    Each file is processed through ColumnMapper to standardize columns.

    Args:
        file_paths: List of paths to CSV files.

    Returns:
        Tuple of (combined DataFrame, list of mapping reports).
    """
    dfs = []
    reports = []

    for path in file_paths:
        try:
            df = pd.read_csv(path)
            mapper = ColumnMapper(df)
            mapper.detect_columns()
            standardized_df = mapper.apply_mapping()
            standardized_df["_source_file"] = path

            dfs.append(standardized_df)
            reports.append({
                "file": path,
                **mapper.get_mapping_report(),
            })

            logger.info(f"Processed file: {path} ({len(standardized_df)} rows)")

        except Exception as e:
            logger.error(f"Failed to process file {path}: {e}")
            reports.append({
                "file": path,
                "error": str(e),
            })

    if dfs:
        combined = pd.concat(dfs, ignore_index=True)
        logger.info(f"Combined {len(dfs)} files into {len(combined)} total rows")
        return combined, reports
    else:
        return pd.DataFrame(columns=["player_name", "date", "data"]), reports


__all__ = ["ColumnMapper", "combine_multiple_files"]

