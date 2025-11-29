"""
Visualization tools for conversational sports load analysis.

Comprehensive tool set for generating charts and visualizations.
"""

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from difflib import SequenceMatcher

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from langchain_core.tools import tool
from loguru import logger

from sports_load_agent.settings import OUTPUTS_DIR

# Use non-interactive backend
plt.switch_backend("Agg")
plt.style.use("seaborn-v0_8-whitegrid")


def _get_df_from_context(context: Dict[str, Any]) -> pd.DataFrame:
    """Extract DataFrame from tool context."""
    df_handle = context.get("processed_data")
    if df_handle is None:
        raise ValueError("No processed data available. Please process data first.")
    return df_handle.load(format="pandas")


def _get_session_id(context: Dict[str, Any]) -> str:
    """Get session ID from context."""
    return context.get("session_id", str(uuid.uuid4())[:8])


def _register_file(context: Dict[str, Any], file_path: str) -> str:
    """Register generated file and return download URL."""
    session_id = _get_session_id(context)
    filename = Path(file_path).name
    if "generated_files" not in context:
        context["generated_files"] = []
    context["generated_files"].append(file_path)
    return f"/api/download/{session_id}/{filename}"


def _fuzzy_match_player(df: pd.DataFrame, query: str, threshold: float = 0.6) -> Optional[str]:
    """Find best matching player name using fuzzy matching."""
    players = df["player_name"].unique()
    query_lower = query.lower().strip()
    
    best_match = None
    best_score = 0
    
    for player in players:
        player_lower = player.lower()
        if query_lower == player_lower:
            return player
        if query_lower in player_lower or player_lower in query_lower:
            score = 0.9
        else:
            score = SequenceMatcher(None, query_lower, player_lower).ratio()
        if score > best_score:
            best_score = score
            best_match = player
    
    return best_match if best_score >= threshold else None


# =============================================================================
# Tool 1: Plot Player Trend
# =============================================================================

@tool
def plot_player_trend(
    context: Dict[str, Any],
    player_name: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate ACWR trend chart for a specific player.
    
    Use this tool when the user asks:
    - "Plot John's ACWR"
    - "Show me player's trend"
    - "Graph of player's load over time"
    
    Args:
        context: Session context (injected automatically)
        player_name: Player name (fuzzy matched)
        start_date: Filter start date (YYYY-MM-DD)
        end_date: Filter end date (YYYY-MM-DD)
    
    Returns:
        Chart file path and download URL
    """
    df = _get_df_from_context(context)
    session_id = _get_session_id(context)
    
    # Fuzzy match
    matched = _fuzzy_match_player(df, player_name)
    if not matched:
        available = df["player_name"].unique().tolist()[:10]
        return {"error": f"Player '{player_name}' not found", "available": available}
    
    # Filter data
    player_df = df[df["player_name"] == matched].copy()
    if start_date and end_date:
        player_df = player_df[
            (player_df["date"] >= pd.to_datetime(start_date)) &
            (player_df["date"] <= pd.to_datetime(end_date))
        ]
    
    player_df = player_df.sort_values("date")
    
    if player_df.empty:
        return {"error": f"No data for {matched} in specified range"}
    
    # Create plot
    fig, ax = plt.subplots(figsize=(12, 5))
    
    ax.plot(player_df["date"], player_df["ACWR"], linewidth=2, color="#2563eb", marker="o", markersize=4)
    
    # Threshold lines
    ax.axhline(y=1.5, color="#ef4444", linestyle="--", alpha=0.7, label="High risk (1.5)")
    ax.axhline(y=0.67, color="#22c55e", linestyle="--", alpha=0.7, label="Undertraining (0.67)")
    ax.axhline(y=1.0, color="#64748b", linestyle=":", alpha=0.5, label="Optimal (1.0)")
    
    ax.set_xlabel("Date", fontsize=11)
    ax.set_ylabel("ACWR", fontsize=11)
    ax.set_title(f"ACWR Trend: {matched}", fontsize=14, fontweight="bold")
    ax.legend(loc="upper right", fontsize=9)
    
    plt.tight_layout()
    
    # Save
    chart_id = str(uuid.uuid4())[:8]
    safe_name = matched.replace(" ", "_").lower()
    output_path = OUTPUTS_DIR / f"{session_id}_trend_{safe_name}_{chart_id}.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    
    download_url = _register_file(context, str(output_path))
    
    logger.info(f"Generated trend chart for {matched}")
    
    return {
        "success": True,
        "player": matched,
        "chart_type": "player_trend",
        "download_url": download_url,
    }


# =============================================================================
# Tool 2: Plot Players Comparison
# =============================================================================

@tool
def plot_players_comparison(
    context: Dict[str, Any],
    player_names: str,
    metric: str = "ACWR",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compare multiple players on the same chart.
    
    Use this tool when the user asks:
    - "Compare John and Mike's trends"
    - "Plot multiple players together"
    - "Side by side trend comparison"
    
    Args:
        context: Session context (injected automatically)
        player_names: Comma-separated player names (e.g., "John, Mike, Sarah")
        metric: "ACWR" or "data" (training load)
        start_date: Filter start date (YYYY-MM-DD)
        end_date: Filter end date (YYYY-MM-DD)
    
    Returns:
        Chart file path and download URL
    """
    df = _get_df_from_context(context)
    session_id = _get_session_id(context)
    
    # Parse and match players
    names = [n.strip() for n in player_names.split(",")]
    matched = []
    not_found = []
    for name in names:
        m = _fuzzy_match_player(df, name)
        if m:
            matched.append(m)
        else:
            not_found.append(name)
    
    if not matched:
        return {"error": "No matching players found", "not_found": not_found}
    
    # Filter data
    if start_date and end_date:
        df = df[
            (df["date"] >= pd.to_datetime(start_date)) &
            (df["date"] <= pd.to_datetime(end_date))
        ]
    
    # Create plot
    fig, ax = plt.subplots(figsize=(12, 6))
    
    colors = plt.cm.tab10(np.linspace(0, 1, len(matched)))
    
    for player, color in zip(matched, colors):
        player_df = df[df["player_name"] == player].sort_values("date")
        ax.plot(player_df["date"], player_df[metric], label=player, linewidth=2, color=color)
    
    # Threshold lines for ACWR
    if metric == "ACWR":
        ax.axhline(y=1.5, color="#ef4444", linestyle="--", alpha=0.5, linewidth=1)
        ax.axhline(y=0.67, color="#22c55e", linestyle="--", alpha=0.5, linewidth=1)
    
    metric_label = "ACWR" if metric == "ACWR" else "Training Load"
    ax.set_xlabel("Date", fontsize=11)
    ax.set_ylabel(metric_label, fontsize=11)
    ax.set_title(f"{metric_label} Comparison", fontsize=14, fontweight="bold")
    ax.legend(loc="upper right", fontsize=9)
    
    plt.tight_layout()
    
    # Save
    chart_id = str(uuid.uuid4())[:8]
    output_path = OUTPUTS_DIR / f"{session_id}_comparison_{chart_id}.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    
    download_url = _register_file(context, str(output_path))
    
    logger.info(f"Generated comparison chart for {len(matched)} players")
    
    result = {
        "success": True,
        "players": matched,
        "chart_type": "players_comparison",
        "download_url": download_url,
    }
    if not_found:
        result["not_found"] = not_found
    
    return result


# =============================================================================
# Tool 3: Plot Team Timeline
# =============================================================================

@tool
def plot_team_timeline(
    context: Dict[str, Any],
    highlight_players: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Plot all players' ACWR trends on one chart.
    
    Use this tool when the user asks:
    - "Show team timeline"
    - "Everyone's ACWR trend"
    - "Team-wide load visualization"
    
    Args:
        context: Session context (injected automatically)
        highlight_players: Optional comma-separated players to highlight (thicker lines)
        start_date: Filter start date (YYYY-MM-DD)
        end_date: Filter end date (YYYY-MM-DD)
    
    Returns:
        Chart file path and download URL
    """
    df = _get_df_from_context(context)
    session_id = _get_session_id(context)
    
    # Filter data
    if start_date and end_date:
        df = df[
            (df["date"] >= pd.to_datetime(start_date)) &
            (df["date"] <= pd.to_datetime(end_date))
        ]
    
    # Parse highlight players
    highlighted = set()
    if highlight_players:
        for name in highlight_players.split(","):
            m = _fuzzy_match_player(df, name.strip())
            if m:
                highlighted.add(m)
    
    # Create plot
    fig, ax = plt.subplots(figsize=(14, 8))
    
    players = df["player_name"].unique()
    cmap = plt.cm.get_cmap("tab20")
    
    for i, player in enumerate(players):
        player_df = df[df["player_name"] == player].sort_values("date")
        color = cmap(i % 20)
        linewidth = 2.5 if player in highlighted else 1
        alpha = 1.0 if player in highlighted else 0.5
        ax.plot(player_df["date"], player_df["ACWR"], label=player, 
                linewidth=linewidth, alpha=alpha, color=color)
    
    # Threshold lines
    ax.axhline(y=1.5, color="#ef4444", linestyle="--", alpha=0.7, linewidth=2)
    ax.axhline(y=0.67, color="#22c55e", linestyle="--", alpha=0.7, linewidth=2)
    
    ax.set_xlabel("Date", fontsize=11)
    ax.set_ylabel("ACWR", fontsize=11)
    ax.set_title("Team ACWR Timeline", fontsize=14, fontweight="bold")
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5), fontsize=8, ncol=1)
    
    plt.tight_layout()
    
    # Save
    chart_id = str(uuid.uuid4())[:8]
    output_path = OUTPUTS_DIR / f"{session_id}_team_timeline_{chart_id}.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    
    download_url = _register_file(context, str(output_path))
    
    logger.info(f"Generated team timeline with {len(players)} players")
    
    return {
        "success": True,
        "player_count": len(players),
        "chart_type": "team_timeline",
        "download_url": download_url,
    }


# =============================================================================
# Tool 4: Plot Category Distribution
# =============================================================================

@tool
def plot_category_distribution(
    context: Dict[str, Any],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Plot pie chart of ACWR category distribution.
    
    Use this tool when the user asks:
    - "Show category distribution"
    - "ACWR breakdown pie chart"
    - "How many high/medium/low?"
    
    Args:
        context: Session context (injected automatically)
        start_date: Filter start date (YYYY-MM-DD)
        end_date: Filter end date (YYYY-MM-DD)
    
    Returns:
        Chart file path and download URL
    """
    df = _get_df_from_context(context)
    session_id = _get_session_id(context)
    
    # Filter data
    if start_date and end_date:
        df = df[
            (df["date"] >= pd.to_datetime(start_date)) &
            (df["date"] <= pd.to_datetime(end_date))
        ]
    
    if "ACWR_category" not in df.columns:
        return {"error": "ACWR category data not available"}
    
    # Get counts
    counts = df["ACWR_category"].value_counts()
    
    # Create plot
    fig, ax = plt.subplots(figsize=(8, 8))
    
    colors = {"high": "#ef4444", "medium": "#fbbf24", "low": "#22c55e"}
    plot_colors = [colors.get(cat, "#94a3b8") for cat in counts.index]
    
    wedges, texts, autotexts = ax.pie(
        counts.values,
        labels=[f"{cat.title()}\n({count})" for cat, count in zip(counts.index, counts.values)],
        autopct="%1.1f%%",
        colors=plot_colors,
        explode=[0.02] * len(counts),
        startangle=90,
    )
    
    for autotext in autotexts:
        autotext.set_fontsize(11)
        autotext.set_fontweight("bold")
    
    ax.set_title("ACWR Category Distribution", fontsize=14, fontweight="bold")
    
    plt.tight_layout()
    
    # Save
    chart_id = str(uuid.uuid4())[:8]
    output_path = OUTPUTS_DIR / f"{session_id}_distribution_{chart_id}.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    
    download_url = _register_file(context, str(output_path))
    
    logger.info("Generated category distribution chart")
    
    return {
        "success": True,
        "distribution": counts.to_dict(),
        "chart_type": "category_distribution",
        "download_url": download_url,
    }


# =============================================================================
# Tool 5: Plot Rankings
# =============================================================================

@tool
def plot_rankings(
    context: Dict[str, Any],
    metric: str = "ACWR",
    top_n: int = 10,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Plot bar chart of top players by metric.
    
    Use this tool when the user asks:
    - "Bar chart of top players"
    - "Visualize rankings"
    - "Show top 10 by ACWR"
    
    Args:
        context: Session context (injected automatically)
        metric: "ACWR", "data" (training load), "short_term_ave", "long_term_ave"
        top_n: Number of players to show (default 10)
        start_date: Filter start date (YYYY-MM-DD)
        end_date: Filter end date (YYYY-MM-DD)
    
    Returns:
        Chart file path and download URL
    """
    df = _get_df_from_context(context)
    session_id = _get_session_id(context)
    
    valid_metrics = ["ACWR", "data", "short_term_ave", "long_term_ave"]
    if metric not in valid_metrics:
        return {"error": f"Invalid metric. Choose from: {valid_metrics}"}
    
    # Filter data
    if start_date and end_date:
        df = df[
            (df["date"] >= pd.to_datetime(start_date)) &
            (df["date"] <= pd.to_datetime(end_date))
        ]
    
    # Calculate means
    player_means = df.groupby("player_name")[metric].mean().dropna()
    player_means = player_means.sort_values(ascending=False).head(top_n)
    
    # Create plot
    fig, ax = plt.subplots(figsize=(10, max(6, top_n * 0.5)))
    
    colors = plt.cm.Blues(np.linspace(0.4, 0.8, len(player_means)))
    bars = ax.barh(range(len(player_means)), player_means.values, color=colors)
    ax.set_yticks(range(len(player_means)))
    ax.set_yticklabels(player_means.index)
    ax.invert_yaxis()
    
    # Add value labels
    for i, (bar, val) in enumerate(zip(bars, player_means.values)):
        ax.text(val + 0.01 * max(player_means.values), i, f"{val:.2f}", va="center", fontsize=9)
    
    # Threshold line for ACWR
    if metric == "ACWR":
        ax.axvline(x=1.5, color="#ef4444", linestyle="--", alpha=0.7, label="High risk")
    
    metric_labels = {"ACWR": "ACWR", "data": "Training Load", 
                     "short_term_ave": "Short-term Avg", "long_term_ave": "Long-term Avg"}
    ax.set_xlabel(f"Average {metric_labels[metric]}", fontsize=11)
    ax.set_title(f"Top {len(player_means)} Players by {metric_labels[metric]}", fontsize=14, fontweight="bold")
    
    plt.tight_layout()
    
    # Save
    chart_id = str(uuid.uuid4())[:8]
    output_path = OUTPUTS_DIR / f"{session_id}_rankings_{metric}_{chart_id}.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    
    download_url = _register_file(context, str(output_path))
    
    logger.info(f"Generated rankings chart for top {top_n} by {metric}")
    
    return {
        "success": True,
        "metric": metric,
        "top_n": len(player_means),
        "chart_type": "rankings",
        "download_url": download_url,
    }


# =============================================================================
# Tool 6: Plot Heatmap
# =============================================================================

@tool
def plot_heatmap(
    context: Dict[str, Any],
    aggregation: str = "week",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Plot player x time heatmap of ACWR.
    
    Use this tool when the user asks:
    - "Show heatmap"
    - "Weekly ACWR heatmap"
    - "Visual overview by week"
    
    Args:
        context: Session context (injected automatically)
        aggregation: "week" or "day"
        start_date: Filter start date (YYYY-MM-DD)
        end_date: Filter end date (YYYY-MM-DD)
    
    Returns:
        Chart file path and download URL
    """
    df = _get_df_from_context(context)
    session_id = _get_session_id(context)
    
    # Filter data
    if start_date and end_date:
        df = df[
            (df["date"] >= pd.to_datetime(start_date)) &
            (df["date"] <= pd.to_datetime(end_date))
        ]
    
    df = df.copy()
    
    # Create period column
    if aggregation == "week":
        df["period"] = df["date"].dt.to_period("W")
    else:
        df["period"] = df["date"].dt.strftime("%Y-%m-%d")
    
    # Pivot
    pivot = df.pivot_table(values="ACWR", index="player_name", columns="period", aggfunc="mean")
    
    # Create plot
    fig, ax = plt.subplots(figsize=(max(12, len(pivot.columns) * 0.5), max(8, len(pivot) * 0.4)))
    
    im = ax.imshow(pivot.values, aspect="auto", cmap="RdYlGn_r", vmin=0.5, vmax=2.0)
    
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index, fontsize=9)
    
    # X ticks
    n_periods = len(pivot.columns)
    tick_step = max(1, n_periods // 12)
    ax.set_xticks(range(0, n_periods, tick_step))
    ax.set_xticklabels([str(pivot.columns[i]) for i in range(0, n_periods, tick_step)], 
                       rotation=45, ha="right", fontsize=8)
    
    ax.set_xlabel("Period", fontsize=11)
    ax.set_ylabel("Player", fontsize=11)
    ax.set_title(f"ACWR Heatmap ({aggregation.title()}ly)", fontsize=14, fontweight="bold")
    
    plt.colorbar(im, ax=ax, label="ACWR")
    
    plt.tight_layout()
    
    # Save
    chart_id = str(uuid.uuid4())[:8]
    output_path = OUTPUTS_DIR / f"{session_id}_heatmap_{chart_id}.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    
    download_url = _register_file(context, str(output_path))
    
    logger.info(f"Generated heatmap ({aggregation}ly aggregation)")
    
    return {
        "success": True,
        "aggregation": aggregation,
        "players": len(pivot),
        "periods": len(pivot.columns),
        "chart_type": "heatmap",
        "download_url": download_url,
    }


__all__ = [
    "plot_player_trend",
    "plot_players_comparison",
    "plot_team_timeline",
    "plot_category_distribution",
    "plot_rankings",
    "plot_heatmap",
]
