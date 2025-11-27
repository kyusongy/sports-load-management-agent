"""
Visualization functions for sports load analysis.

Generates charts for load trends, player comparisons, and distribution analysis.
All functions save plots to files for API serving.
"""

from pathlib import Path
from typing import List, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from loguru import logger

# Use non-interactive backend for server-side rendering
plt.switch_backend("Agg")

# Set default style
plt.style.use("seaborn-v0_8-whitegrid")


def plot_load_trend(
    df: pd.DataFrame,
    player: str,
    output_path: Path,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    """
    Plot a player's load trend over time.

    Args:
        df: Processed DataFrame with 'load' column.
        player: Player name to plot.
        output_path: Path to save the plot.
        start_date: Optional start date filter.
        end_date: Optional end date filter.

    Returns:
        Path to saved plot file.
    """
    subset = df[df["player_name"] == player].sort_values("date")

    if start_date:
        subset = subset[subset["date"] >= pd.to_datetime(start_date)]
    if end_date:
        subset = subset[subset["date"] <= pd.to_datetime(end_date)]

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(subset["date"], subset["load"], linewidth=2, color="#2563eb", marker="o", markersize=4)

    # Add threshold lines
    ax.axhline(y=1.5, color="#ef4444", linestyle="--", alpha=0.7, label="High threshold (1.5)")
    ax.axhline(y=0.67, color="#22c55e", linestyle="--", alpha=0.7, label="Low threshold (0.67)")
    ax.axhline(y=1.0, color="#64748b", linestyle=":", alpha=0.5, label="Optimal (1.0)")

    ax.set_xlabel("Date", fontsize=11)
    ax.set_ylabel("ACWR (Load)", fontsize=11)
    ax.set_title(f"Load Trend for {player}", fontsize=14, fontweight="bold")
    ax.legend(loc="upper right", fontsize=9)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    logger.info(f"Saved load trend plot to {output_path}")
    return str(output_path)


def plot_short_and_long_averages(
    df: pd.DataFrame,
    player: str,
    output_path: Path,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    """
    Plot short-term and long-term averages for a player.

    Args:
        df: Processed DataFrame with average columns.
        player: Player name to plot.
        output_path: Path to save the plot.
        start_date: Optional start date filter.
        end_date: Optional end date filter.

    Returns:
        Path to saved plot file.
    """
    subset = df[df["player_name"] == player].sort_values("date")

    if start_date:
        subset = subset[subset["date"] >= pd.to_datetime(start_date)]
    if end_date:
        subset = subset[subset["date"] <= pd.to_datetime(end_date)]

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(
        subset["date"],
        subset["short_term_ave"],
        label="Short-term (3-day)",
        linewidth=2,
        color="#f59e0b",
    )
    ax.plot(
        subset["date"],
        subset["long_term_ave"],
        label="Long-term (2-week)",
        linewidth=2,
        color="#8b5cf6",
    )

    ax.set_xlabel("Date", fontsize=11)
    ax.set_ylabel("Training Load", fontsize=11)
    ax.set_title(f"Short vs Long-term Averages for {player}", fontsize=14, fontweight="bold")
    ax.legend(loc="upper right", fontsize=10)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    logger.info(f"Saved averages plot to {output_path}")
    return str(output_path)


def plot_top_players_bar(
    df: pd.DataFrame,
    metric: str,
    n: int,
    output_path: Path,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    """
    Bar chart of top N players by average metric.

    Args:
        df: Processed DataFrame.
        metric: Column to rank by ('load', 'short_term_ave', 'long_term_ave', 'data').
        n: Number of top players.
        output_path: Path to save the plot.
        start_date: Optional start date filter.
        end_date: Optional end date filter.

    Returns:
        Path to saved plot file.
    """
    # Human-readable labels for metrics
    metric_labels = {
        "load": "ACWR",
        "data": "Training Load (sRPE)",
        "short_term_ave": "Short-term Average",
        "long_term_ave": "Long-term Average",
    }
    metric_label = metric_labels.get(metric, metric.replace('_', ' ').title())

    subset = df.copy()

    if start_date:
        subset = subset[subset["date"] >= pd.to_datetime(start_date)]
    if end_date:
        subset = subset[subset["date"] <= pd.to_datetime(end_date)]

    means = subset.groupby("player_name")[metric].mean().dropna().sort_values(ascending=False)
    top_players = means.head(n)

    fig, ax = plt.subplots(figsize=(10, 6))

    colors = plt.cm.Blues(np.linspace(0.4, 0.8, len(top_players)))
    bars = ax.barh(range(len(top_players)), top_players.values, color=colors)
    ax.set_yticks(range(len(top_players)))
    ax.set_yticklabels(top_players.index)
    ax.invert_yaxis()

    ax.set_xlabel(f"Average {metric_label}", fontsize=11)
    ax.set_title(f"Top {n} Players by {metric_label}", fontsize=14, fontweight="bold")

    # Add value labels
    for i, (bar, val) in enumerate(zip(bars, top_players.values)):
        ax.text(val + 0.01 * max(top_players.values), i, f"{val:.2f}", va="center", fontsize=9)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    logger.info(f"Saved top players bar chart to {output_path}")
    return str(output_path)


def plot_load_quality_distribution(df: pd.DataFrame, output_path: Path) -> str:
    """
    Pie chart showing distribution of load quality categories.

    Args:
        df: Processed DataFrame with 'load_quality' column.
        output_path: Path to save the plot.

    Returns:
        Path to saved plot file.
    """
    quality_counts = df["load_quality"].value_counts()

    fig, ax = plt.subplots(figsize=(8, 8))

    colors = {"high": "#ef4444", "medium": "#fbbf24", "low": "#22c55e"}
    plot_colors = [colors.get(cat, "#94a3b8") for cat in quality_counts.index]

    wedges, texts, autotexts = ax.pie(
        quality_counts.values,
        labels=quality_counts.index,
        autopct="%1.1f%%",
        colors=plot_colors,
        explode=[0.02] * len(quality_counts),
        shadow=False,
        startangle=90,
    )

    for autotext in autotexts:
        autotext.set_fontsize(11)
        autotext.set_fontweight("bold")

    ax.set_title("Load Quality Distribution", fontsize=14, fontweight="bold")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    logger.info(f"Saved load quality distribution to {output_path}")
    return str(output_path)


def plot_team_load_timeline(df: pd.DataFrame, output_path: Path) -> str:
    """
    Timeline showing all players' load trends.

    Args:
        df: Processed DataFrame.
        output_path: Path to save the plot.

    Returns:
        Path to saved plot file.
    """
    fig, ax = plt.subplots(figsize=(14, 8))

    players = df["player_name"].unique()
    cmap = plt.cm.get_cmap("tab20")

    for i, player in enumerate(players):
        player_data = df[df["player_name"] == player].sort_values("date")
        color = cmap(i % 20)
        ax.plot(
            player_data["date"],
            player_data["load"],
            label=player,
            alpha=0.7,
            linewidth=1.5,
            color=color,
        )

    # Add threshold lines
    ax.axhline(y=1.5, color="#ef4444", linestyle="--", alpha=0.5, linewidth=2)
    ax.axhline(y=0.67, color="#22c55e", linestyle="--", alpha=0.5, linewidth=2)

    ax.set_xlabel("Date", fontsize=11)
    ax.set_ylabel("ACWR (Load)", fontsize=11)
    ax.set_title("Team Load Timeline", fontsize=14, fontweight="bold")

    # Put legend outside plot
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5), fontsize=8, ncol=1)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    logger.info(f"Saved team timeline to {output_path}")
    return str(output_path)


def plot_player_load_heatmap(df: pd.DataFrame, output_path: Path) -> str:
    """
    Heatmap showing load quality by player over time (weekly aggregation).

    Args:
        df: Processed DataFrame.
        output_path: Path to save the plot.

    Returns:
        Path to saved plot file.
    """
    # Create weekly aggregation
    df_copy = df.copy()
    df_copy["week"] = df_copy["date"].dt.to_period("W")

    # Pivot to create player x week matrix
    pivot = df_copy.pivot_table(
        values="load",
        index="player_name",
        columns="week",
        aggfunc="mean",
    )

    fig, ax = plt.subplots(figsize=(16, max(8, len(pivot) * 0.4)))

    # Create heatmap
    im = ax.imshow(pivot.values, aspect="auto", cmap="RdYlGn_r", vmin=0.5, vmax=2.0)

    # Set ticks
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index, fontsize=9)

    # Show fewer x-ticks for readability
    n_weeks = len(pivot.columns)
    tick_step = max(1, n_weeks // 10)
    ax.set_xticks(range(0, n_weeks, tick_step))
    ax.set_xticklabels([str(pivot.columns[i]) for i in range(0, n_weeks, tick_step)], rotation=45, ha="right", fontsize=8)

    ax.set_xlabel("Week", fontsize=11)
    ax.set_ylabel("Player", fontsize=11)
    ax.set_title("Player Load Heatmap (Weekly Average)", fontsize=14, fontweight="bold")

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, label="ACWR (Load)")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    logger.info(f"Saved player heatmap to {output_path}")
    return str(output_path)


class LoadVisualizer:
    """
    Visualization manager for generating default set of charts.
    """

    def __init__(self, df: pd.DataFrame, output_dir: Path):
        """
        Initialize visualizer.

        Args:
            df: Processed DataFrame from LoadCalculator.
            output_dir: Directory to save plot files.
        """
        self.df = df
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_default_set(self, session_id: str) -> List[str]:
        """
        Generate the default set of visualizations.

        Args:
            session_id: Session identifier for file naming.

        Returns:
            List of paths to generated plot files.
        """
        plots = []

        # 1. Top 5 players by average load
        try:
            path = self.output_dir / f"{session_id}_top_players_load.png"
            plots.append(plot_top_players_bar(self.df, "load", 5, path))
        except Exception as e:
            logger.warning(f"Failed to generate top players chart: {e}")

        # 2. Load quality distribution
        try:
            path = self.output_dir / f"{session_id}_load_distribution.png"
            plots.append(plot_load_quality_distribution(self.df, path))
        except Exception as e:
            logger.warning(f"Failed to generate distribution chart: {e}")

        # 3. Team load timeline
        try:
            path = self.output_dir / f"{session_id}_team_timeline.png"
            plots.append(plot_team_load_timeline(self.df, path))
        except Exception as e:
            logger.warning(f"Failed to generate team timeline: {e}")

        # 4. Player heatmap
        try:
            path = self.output_dir / f"{session_id}_player_heatmap.png"
            plots.append(plot_player_load_heatmap(self.df, path))
        except Exception as e:
            logger.warning(f"Failed to generate heatmap: {e}")

        # 5. Top 5 players by training load (raw data)
        try:
            path = self.output_dir / f"{session_id}_top_players_training.png"
            plots.append(plot_top_players_bar(self.df, "data", 5, path))
        except Exception as e:
            logger.warning(f"Failed to generate training load chart: {e}")

        logger.info(f"Generated {len(plots)} visualizations for session {session_id}")
        return plots


__all__ = [
    "LoadVisualizer",
    "plot_load_trend",
    "plot_short_and_long_averages",
    "plot_top_players_bar",
    "plot_load_quality_distribution",
    "plot_team_load_timeline",
    "plot_player_load_heatmap",
]

