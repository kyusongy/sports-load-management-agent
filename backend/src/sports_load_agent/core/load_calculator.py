"""
Load Calculator for sports training load analysis.

Computes short-term and long-term averages, ACWR (Acute:Chronic Workload Ratio),
and categorizes load quality. Ported from the analysis template with sRPE support.
"""

from typing import List, Optional

import numpy as np
import pandas as pd
from loguru import logger


class LoadCalculator:
    """
    Compute short-term and long-term averages and load metrics.

    This class assumes the DataFrame has standardized columns:
    - 'player_name': Player identifier
    - 'date': Date of the training session
    - 'data': Training load value (raw load or calculated sRPE)
    """

    def __init__(self, df: pd.DataFrame):
        """
        Initialize with a DataFrame.

        Args:
            df: DataFrame with columns 'player_name', 'date', 'data'
        """
        self.df = df.copy()
        self.df["date"] = pd.to_datetime(self.df["date"], errors="coerce")
        self.df["player_name"] = self.df["player_name"].astype(str)

    def clean_data(self) -> None:
        """
        Clean the data column and dates.

        - Convert 'data' column to numeric (handles 'x', 'X', '-', etc.)
        - Ensure dates are valid
        - Drop rows with missing dates
        """
        # Clean data column
        self.df["data"] = pd.to_numeric(self.df["data"], errors="coerce")

        # Ensure date column is datetime
        self.df["date"] = pd.to_datetime(self.df["date"], errors="coerce")

        # Count stats before dropping
        missing_data = self.df["data"].isna().sum()
        missing_dates = self.df["date"].isna().sum()

        # Drop rows with missing dates (can't compute load without date)
        initial_len = len(self.df)
        self.df = self.df.dropna(subset=["date"])

        logger.info(
            f"Cleaned data: {missing_data} missing load values, "
            f"{missing_dates} missing dates (dropped), "
            f"{len(self.df)}/{initial_len} rows retained"
        )

    def _compute_short_term_for_player(self, data_series: pd.Series) -> pd.Series:
        """
        Compute 3-day short-term average per player for a series of 'data' values
        sorted by date.

        Rules:
        - For any day, look backwards (including that day) and collect the most
          recent 3 non-NaN 'data' values.
        - If current day is NaN, skip it and go back further until 3 non-NaN found.
        - For first 2 days (by order), output NaN (not enough history).
        - If cannot find 3 non-NaN values, output NaN.
        """
        short_vals = []
        non_na_values: List[float] = []

        for idx, val in enumerate(data_series):
            if not pd.isna(val):
                non_na_values.append(float(val))
            if idx < 2 or len(non_na_values) < 3:
                short_vals.append(np.nan)
            else:
                # Last 3 non-NaN values
                window_vals = non_na_values[-3:]
                short_vals.append(float(np.mean(window_vals)))

        return pd.Series(short_vals, index=data_series.index).round(2)

    def add_short_term_average(self) -> None:
        """Add the column 'short_term_ave' to the DataFrame."""
        self.df = self.df.sort_values(["player_name", "date"])
        self.df["short_term_ave"] = np.nan

        for player, group in self.df.groupby("player_name"):
            group_sorted = group.sort_values("date")
            short_series = self._compute_short_term_for_player(group_sorted["data"])
            self.df.loc[group_sorted.index, "short_term_ave"] = short_series

        logger.info("Added short_term_ave column")

    def _assign_weeks(self) -> None:
        """
        Add a 'week_index' column:
        - week_index == 0: from the first date until the first Saturday (inclusive).
        - week_index >= 1: each week starts on Sunday and ends on Saturday.
        """
        # Filter out NaT values for calculating start date
        valid_dates = self.df["date"].dropna()
        if valid_dates.empty:
            self.df["week_index"] = 0
            return

        start_date = valid_dates.min().normalize()
        # weekday(): Monday = 0, Sunday = 6
        offset_to_sunday = (6 - start_date.weekday()) % 7
        first_sunday = start_date + pd.Timedelta(days=offset_to_sunday)

        def week_index_for_date(d: pd.Timestamp) -> int:
            if pd.isna(d):
                return -1  # Mark invalid dates
            d = d.normalize()
            if d < first_sunday:
                return 0
            delta_days = (d - first_sunday).days
            return 1 + delta_days // 7

        self.df["week_index"] = self.df["date"].apply(week_index_for_date)

    def _compute_long_term_for_player(self, player_df: pd.DataFrame) -> pd.Series:
        """
        Compute long-term weekly averages for a single player.

        Rules:
        - Week is defined by 'week_index'.
        - For any week w (w >= 2), take all non-NaN 'data' values from weeks
          w-2 and w-1, and compute their arithmetic mean.
        - Assign the same long-term average to all rows of that player in week w.
        - Weeks 0 and 1 receive NaN (not enough history).
        """
        result = pd.Series(np.nan, index=player_df.index, dtype=float)
        weeks = sorted(player_df["week_index"].unique())

        for w in weeks:
            if w < 2:
                continue
            prev_weeks = [w - 2, w - 1]
            mask_prev = player_df["week_index"].isin(prev_weeks)
            values_prev = player_df.loc[mask_prev, "data"].dropna()
            if values_prev.empty:
                continue
            long_val = values_prev.mean()
            mask_current = player_df["week_index"] == w
            result.loc[mask_current] = long_val

        return result.round(2)

    def add_long_term_average(self) -> None:
        """Add the column 'long_term_ave' to the DataFrame."""
        if "week_index" not in self.df.columns:
            self._assign_weeks()

        self.df = self.df.sort_values(["player_name", "date"])
        self.df["long_term_ave"] = np.nan

        for player, group in self.df.groupby("player_name"):
            group_sorted = group.sort_values("date")
            long_series = self._compute_long_term_for_player(group_sorted)
            self.df.loc[group_sorted.index, "long_term_ave"] = long_series

        logger.info("Added long_term_ave column")

    def add_load_and_quality(self) -> None:
        """
        Compute:
        - load = short_term_ave / long_term_ave (ACWR)
        - load_quality: 'high' (load > 1.5), 'low' (load < 0.67), 'medium' otherwise

        ACWR (Acute:Chronic Workload Ratio) interpretation:
        - High (>1.5): Increased injury risk - athlete may be overloaded
        - Medium (0.67-1.5): Sweet spot - appropriate loading
        - Low (<0.67): Undertraining - fitness may be declining
        """
        if "short_term_ave" not in self.df.columns:
            raise ValueError(
                "short_term_ave column missing. Call add_short_term_average() first."
            )
        if "long_term_ave" not in self.df.columns:
            raise ValueError(
                "long_term_ave column missing. Call add_long_term_average() first."
            )

        self.df["load"] = self.df["short_term_ave"] / self.df["long_term_ave"]
        mask_invalid = (
            self.df["short_term_ave"].isna() | self.df["long_term_ave"].isna()
        )
        self.df.loc[mask_invalid, "load"] = np.nan
        self.df["load"] = self.df["load"].round(4)

        def categorize(load: float) -> Optional[str]:
            if pd.isna(load):
                return None
            if load > 1.5:
                return "high"
            if load < 0.6667:
                return "low"
            return "medium"

        self.df["load_quality"] = self.df["load"].apply(categorize)
        logger.info("Added load and load_quality columns")

    def process_all(self) -> "LoadCalculator":
        """
        Run the full processing pipeline.

        Returns self for method chaining.
        """
        self.clean_data()
        self.add_short_term_average()
        self.add_long_term_average()
        self.add_load_and_quality()
        return self

    def get_result(self) -> pd.DataFrame:
        """Return the processed DataFrame (a copy)."""
        return self.df.copy()

    def get_summary_stats(self) -> dict:
        """
        Get summary statistics for the processed data.

        Returns:
            Dictionary with summary statistics.
        """
        stats = {
            "total_records": len(self.df),
            "unique_players": self.df["player_name"].nunique(),
            "date_range": {
                "start": self.df["date"].min().isoformat(),
                "end": self.df["date"].max().isoformat(),
            },
            "missing_data_count": int(self.df["data"].isna().sum()),
        }

        if "load_quality" in self.df.columns:
            quality_counts = self.df["load_quality"].value_counts().to_dict()
            stats["load_quality_distribution"] = quality_counts

            # Players with high load concern
            high_load_players = (
                self.df[self.df["load_quality"] == "high"]["player_name"]
                .unique()
                .tolist()
            )
            stats["high_load_players"] = high_load_players

        if "load" in self.df.columns:
            stats["load_stats"] = {
                "mean": round(self.df["load"].mean(), 4),
                "median": round(self.df["load"].median(), 4),
                "min": round(self.df["load"].min(), 4),
                "max": round(self.df["load"].max(), 4),
            }

        return stats

    def save_processed_data(
        self,
        csv_path: str = "processed_data.csv",
        excel_path: str = "processed_data_colored.xlsx",
    ) -> tuple[str, str]:
        """
        Save processed data to CSV and colored Excel.

        Args:
            csv_path: Path for CSV output.
            excel_path: Path for Excel output with conditional formatting.

        Returns:
            Tuple of (csv_path, excel_path).
        """
        # Save CSV
        self.df.to_csv(csv_path, index=False)
        logger.info(f"Saved CSV to {csv_path}")

        # Save Excel with conditional formatting
        try:
            with pd.ExcelWriter(excel_path, engine="xlsxwriter") as writer:
                self.df.to_excel(writer, sheet_name="data", index=False)
                workbook = writer.book
                worksheet = writer.sheets["data"]

                if "load_quality" in self.df.columns:
                    q_col_idx = self.df.columns.get_loc("load_quality")

                    # Define formats
                    red_format = workbook.add_format({"bg_color": "#FF9999"})
                    yellow_format = workbook.add_format({"bg_color": "#FFFF99"})
                    green_format = workbook.add_format({"bg_color": "#CCFFCC"})

                    first_data_row = 1
                    last_data_row = len(self.df)

                    # High -> red
                    worksheet.conditional_format(
                        first_data_row,
                        q_col_idx,
                        last_data_row,
                        q_col_idx,
                        {
                            "type": "cell",
                            "criteria": "==",
                            "value": '"high"',
                            "format": red_format,
                        },
                    )
                    # Medium -> yellow
                    worksheet.conditional_format(
                        first_data_row,
                        q_col_idx,
                        last_data_row,
                        q_col_idx,
                        {
                            "type": "cell",
                            "criteria": "==",
                            "value": '"medium"',
                            "format": yellow_format,
                        },
                    )
                    # Low -> green
                    worksheet.conditional_format(
                        first_data_row,
                        q_col_idx,
                        last_data_row,
                        q_col_idx,
                        {
                            "type": "cell",
                            "criteria": "==",
                            "value": '"low"',
                            "format": green_format,
                        },
                    )

            logger.info(f"Saved colored Excel to {excel_path}")
        except Exception as exc:
            logger.warning(f"Could not create colored Excel file: {exc}")
            # Fallback to simple Excel
            self.df.to_excel(excel_path, index=False)

        return csv_path, excel_path


__all__ = ["LoadCalculator"]

