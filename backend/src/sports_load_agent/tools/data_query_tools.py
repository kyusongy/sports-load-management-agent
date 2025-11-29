"""
Data query tools for conversational sports load analysis.

Comprehensive tool set covering common queries about player training load data.
"""

from typing import Any, Dict, List, Optional
from difflib import SequenceMatcher

import pandas as pd
from langchain_core.tools import tool
from loguru import logger


def _get_df_from_context(context: Dict[str, Any]) -> pd.DataFrame:
    """Extract DataFrame from tool context."""
    df_handle = context.get("processed_data")
    if df_handle is None:
        raise ValueError("No processed data available. Please process data first.")
    return df_handle.load(format="pandas")


def _fuzzy_match_player(df: pd.DataFrame, query: str, threshold: float = 0.6) -> Optional[str]:
    """
    Find best matching player name using fuzzy matching.
    
    Args:
        df: DataFrame with player_name column
        query: User's input for player name
        threshold: Minimum similarity score (0-1)
    
    Returns:
        Best matching player name or None if no match above threshold
    """
    players = df["player_name"].unique()
    query_lower = query.lower().strip()
    
    best_match = None
    best_score = 0
    
    for player in players:
        player_lower = player.lower()
        
        # Exact match
        if query_lower == player_lower:
            return player
        
        # Contains match (high priority)
        if query_lower in player_lower or player_lower in query_lower:
            score = 0.9
        else:
            # Fuzzy match
            score = SequenceMatcher(None, query_lower, player_lower).ratio()
        
        if score > best_score:
            best_score = score
            best_match = player
    
    return best_match if best_score >= threshold else None


def _find_players(df: pd.DataFrame, query: str) -> List[str]:
    """
    Find all players matching the query (for multi-player operations).
    Returns list of matching player names.
    """
    players = df["player_name"].unique()
    query_lower = query.lower().strip()
    
    matches = []
    for player in players:
        player_lower = player.lower()
        if query_lower in player_lower or player_lower in query_lower:
            matches.append(player)
        elif SequenceMatcher(None, query_lower, player_lower).ratio() >= 0.6:
            matches.append(player)
    
    return matches


# =============================================================================
# Tool 1: Data Summary
# =============================================================================

@tool
def get_data_summary(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get overall summary statistics of the training load dataset.
    
    Use this tool when the user asks about:
    - General overview of the data
    - How many players/records
    - Date range of the dataset
    - Overall ACWR statistics
    - Distribution of risk categories
    
    Args:
        context: Session context (injected automatically)
    
    Returns:
        Summary with player count, date range, ACWR stats, category distribution
    """
    df = _get_df_from_context(context)
    
    # Basic counts
    total_records = len(df)
    unique_players = int(df["player_name"].nunique())
    
    # Date range
    date_min = df["date"].min()
    date_max = df["date"].max()
    
    # ACWR statistics
    acwr_series = df["ACWR"].dropna()
    acwr_stats = {}
    if not acwr_series.empty:
        acwr_stats = {
            "mean": round(float(acwr_series.mean()), 3),
            "median": round(float(acwr_series.median()), 3),
            "min": round(float(acwr_series.min()), 3),
            "max": round(float(acwr_series.max()), 3),
            "std": round(float(acwr_series.std()), 3),
        }
    
    # Category distribution
    category_dist = {}
    if "ACWR_category" in df.columns:
        counts = df["ACWR_category"].value_counts()
        total_categorized = counts.sum()
        for cat in ["high", "medium", "low"]:
            if cat in counts.index:
                category_dist[cat] = {
                    "count": int(counts[cat]),
                    "percentage": round(100 * counts[cat] / total_categorized, 1)
                }
    
    logger.info(f"Data summary: {unique_players} players, {total_records} records")
    
    return {
        "total_records": total_records,
        "unique_players": unique_players,
        "date_range": {
            "start": date_min.strftime("%Y-%m-%d"),
            "end": date_max.strftime("%Y-%m-%d"),
            "days": (date_max - date_min).days + 1
        },
        "ACWR_statistics": acwr_stats,
        "category_distribution": category_dist,
    }


# =============================================================================
# Tool 2: Get Player Data
# =============================================================================

@tool
def get_player_data(
    context: Dict[str, Any],
    player_name: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get detailed data for a specific player.
    
    Use this tool when the user asks about:
    - A specific player's status
    - Individual player's ACWR or training load
    - Player's recent performance
    
    Args:
        context: Session context (injected automatically)
        player_name: Name of the player (fuzzy matched)
        start_date: Filter start date (YYYY-MM-DD). Required if filtering by date.
        end_date: Filter end date (YYYY-MM-DD). Required if filtering by date.
    
    Returns:
        Player's statistics and recent records
    """
    df = _get_df_from_context(context)
    
    # Fuzzy match player name
    matched_player = _fuzzy_match_player(df, player_name)
    if not matched_player:
        available = df["player_name"].unique().tolist()[:10]
        return {
            "error": f"Player '{player_name}' not found",
            "suggestion": "Available players include: " + ", ".join(available)
        }
    
    # Filter to player
    player_df = df[df["player_name"] == matched_player].copy()
    
    # Apply date filters if provided
    if start_date and end_date:
        player_df = player_df[
            (player_df["date"] >= pd.to_datetime(start_date)) &
            (player_df["date"] <= pd.to_datetime(end_date))
        ]
    
    if player_df.empty:
        return {"error": f"No data for {matched_player} in the specified date range"}
    
    player_df = player_df.sort_values("date", ascending=False)
    
    # Calculate stats
    acwr_series = player_df["ACWR"].dropna()
    stats = {}
    if not acwr_series.empty:
        stats = {
            "current_ACWR": round(float(acwr_series.iloc[0]), 3),
            "mean_ACWR": round(float(acwr_series.mean()), 3),
            "max_ACWR": round(float(acwr_series.max()), 3),
            "min_ACWR": round(float(acwr_series.min()), 3),
        }
    
    # Current status
    latest = player_df.iloc[0]
    current_category = latest.get("ACWR_category", "unknown")
    
    # Recent records (last 10)
    recent = []
    for _, row in player_df.head(10).iterrows():
        recent.append({
            "date": row["date"].strftime("%Y-%m-%d"),
            "training_load": round(float(row["data"]), 1) if pd.notna(row["data"]) else None,
            "ACWR": round(float(row["ACWR"]), 3) if pd.notna(row["ACWR"]) else None,
            "category": row.get("ACWR_category"),
        })
    
    logger.info(f"Retrieved data for player: {matched_player}")
    
    return {
        "player_name": matched_player,
        "current_status": current_category,
        "statistics": stats,
        "record_count": len(player_df),
        "date_range": {
            "start": player_df["date"].min().strftime("%Y-%m-%d"),
            "end": player_df["date"].max().strftime("%Y-%m-%d"),
        },
        "recent_records": recent,
    }


# =============================================================================
# Tool 3: List Players
# =============================================================================

@tool
def list_players(
    context: Dict[str, Any],
    sort_by: str = "name",
    limit: int = 50,
) -> Dict[str, Any]:
    """
    List all players in the dataset with their current status.
    
    Use this tool when the user asks:
    - "Who's in the dataset?"
    - "List all players"
    - "Show me all athletes"
    
    Args:
        context: Session context (injected automatically)
        sort_by: Sort order - "name", "ACWR" (highest first), or "risk" (high risk first)
        limit: Maximum players to return (default 50)
    
    Returns:
        List of players with their latest ACWR and status
    """
    df = _get_df_from_context(context)
    
    # Get latest record for each player
    latest_per_player = df.sort_values("date").groupby("player_name").last().reset_index()
    
    players = []
    for _, row in latest_per_player.iterrows():
        players.append({
            "name": row["player_name"],
            "latest_ACWR": round(float(row["ACWR"]), 3) if pd.notna(row["ACWR"]) else None,
            "category": row.get("ACWR_category"),
            "latest_date": row["date"].strftime("%Y-%m-%d"),
        })
    
    # Sort
    if sort_by == "ACWR":
        players.sort(key=lambda x: x["latest_ACWR"] or 0, reverse=True)
    elif sort_by == "risk":
        risk_order = {"high": 0, "medium": 1, "low": 2, None: 3}
        players.sort(key=lambda x: risk_order.get(x["category"], 3))
    else:  # name
        players.sort(key=lambda x: x["name"].lower())
    
    players = players[:limit]
    
    logger.info(f"Listed {len(players)} players")
    
    return {
        "total_players": len(latest_per_player),
        "showing": len(players),
        "sort_by": sort_by,
        "players": players,
    }


# =============================================================================
# Tool 4: Get High Risk Players
# =============================================================================

@tool
def get_high_risk_players(
    context: Dict[str, Any],
    threshold: float = 1.5,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get players with high ACWR indicating injury risk.
    
    Use this tool when the user asks:
    - "Who's at high risk?"
    - "Which players have high ACWR?"
    - "Injury risk assessment"
    - "Who's overtraining?"
    
    ACWR > 1.5 indicates increased injury risk.
    
    Args:
        context: Session context (injected automatically)
        threshold: ACWR threshold for high risk (default 1.5)
        start_date: Filter start date (YYYY-MM-DD)
        end_date: Filter end date (YYYY-MM-DD)
    
    Returns:
        List of high-risk players with their ACWR statistics
    """
    df = _get_df_from_context(context)
    
    # Apply date filter if provided
    if start_date and end_date:
        df = df[
            (df["date"] >= pd.to_datetime(start_date)) &
            (df["date"] <= pd.to_datetime(end_date))
        ]
    
    # Find high ACWR records
    high_df = df[df["ACWR"] > threshold].copy()
    
    if high_df.empty:
        return {
            "message": f"No players found with ACWR > {threshold}",
            "threshold": threshold,
            "high_risk_players": [],
        }
    
    # Aggregate by player
    player_stats = high_df.groupby("player_name").agg(
        occurrences=("ACWR", "count"),
        max_ACWR=("ACWR", "max"),
        mean_ACWR=("ACWR", "mean"),
        latest_date=("date", "max"),
    ).round(3)
    
    player_stats = player_stats.sort_values("max_ACWR", ascending=False)
    
    players = []
    for player, row in player_stats.iterrows():
        players.append({
            "name": player,
            "high_ACWR_occurrences": int(row["occurrences"]),
            "max_ACWR": float(row["max_ACWR"]),
            "mean_high_ACWR": float(row["mean_ACWR"]),
            "latest_high_date": row["latest_date"].strftime("%Y-%m-%d"),
        })
    
    logger.info(f"Found {len(players)} high-risk players (ACWR > {threshold})")
    
    return {
        "threshold": threshold,
        "high_risk_count": len(players),
        "high_risk_players": players,
    }


# =============================================================================
# Tool 5: Get Undertraining Players
# =============================================================================

@tool
def get_undertraining_players(
    context: Dict[str, Any],
    threshold: float = 0.67,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get players with low ACWR indicating potential undertraining.
    
    Use this tool when the user asks:
    - "Who's undertraining?"
    - "Low ACWR players?"
    - "Who needs more training?"
    - "Detraining risk"
    
    ACWR < 0.67 may indicate undertraining or detraining.
    
    Args:
        context: Session context (injected automatically)
        threshold: ACWR threshold for undertraining (default 0.67)
        start_date: Filter start date (YYYY-MM-DD)
        end_date: Filter end date (YYYY-MM-DD)
    
    Returns:
        List of undertraining players with their ACWR statistics
    """
    df = _get_df_from_context(context)
    
    # Apply date filter if provided
    if start_date and end_date:
        df = df[
            (df["date"] >= pd.to_datetime(start_date)) &
            (df["date"] <= pd.to_datetime(end_date))
        ]
    
    # Find low ACWR records
    low_df = df[df["ACWR"] < threshold].copy()
    
    if low_df.empty:
        return {
            "message": f"No players found with ACWR < {threshold}",
            "threshold": threshold,
            "undertraining_players": [],
        }
    
    # Aggregate by player
    player_stats = low_df.groupby("player_name").agg(
        occurrences=("ACWR", "count"),
        min_ACWR=("ACWR", "min"),
        mean_ACWR=("ACWR", "mean"),
        latest_date=("date", "max"),
    ).round(3)
    
    player_stats = player_stats.sort_values("min_ACWR", ascending=True)
    
    players = []
    for player, row in player_stats.iterrows():
        players.append({
            "name": player,
            "low_ACWR_occurrences": int(row["occurrences"]),
            "min_ACWR": float(row["min_ACWR"]),
            "mean_low_ACWR": float(row["mean_ACWR"]),
            "latest_low_date": row["latest_date"].strftime("%Y-%m-%d"),
        })
    
    logger.info(f"Found {len(players)} undertraining players (ACWR < {threshold})")
    
    return {
        "threshold": threshold,
        "undertraining_count": len(players),
        "undertraining_players": players,
    }


# =============================================================================
# Tool 6: Get Player Rankings
# =============================================================================

@tool
def get_player_rankings(
    context: Dict[str, Any],
    metric: str = "ACWR",
    top_n: int = 10,
    ascending: bool = False,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Rank players by a specified metric.
    
    Use this tool when the user asks:
    - "Top players by ACWR"
    - "Who trained the hardest?"
    - "Highest training load"
    - "Rank players"
    
    Args:
        context: Session context (injected automatically)
        metric: Metric to rank by - "ACWR", "data" (training load), "short_term_ave", "long_term_ave"
        top_n: Number of players to return (default 10)
        ascending: If True, show lowest first; if False, show highest first (default)
        start_date: Filter start date (YYYY-MM-DD)
        end_date: Filter end date (YYYY-MM-DD)
    
    Returns:
        Ranked list of players by the specified metric
    """
    df = _get_df_from_context(context)
    
    valid_metrics = ["ACWR", "data", "short_term_ave", "long_term_ave"]
    if metric not in valid_metrics:
        return {"error": f"Invalid metric. Choose from: {valid_metrics}"}
    
    # Apply date filter if provided
    if start_date and end_date:
        df = df[
            (df["date"] >= pd.to_datetime(start_date)) &
            (df["date"] <= pd.to_datetime(end_date))
        ]
    
    # Calculate mean per player
    player_means = df.groupby("player_name")[metric].mean().dropna()
    player_means = player_means.sort_values(ascending=ascending).head(top_n)
    
    metric_labels = {
        "ACWR": "ACWR",
        "data": "Training Load",
        "short_term_ave": "Short-term Average",
        "long_term_ave": "Long-term Average",
    }
    
    rankings = []
    for rank, (player, value) in enumerate(player_means.items(), 1):
        rankings.append({
            "rank": rank,
            "player": player,
            "value": round(float(value), 3),
        })
    
    logger.info(f"Generated rankings by {metric}, top {top_n}")
    
    return {
        "metric": metric,
        "metric_label": metric_labels[metric],
        "order": "ascending" if ascending else "descending",
        "rankings": rankings,
    }


# =============================================================================
# Tool 7: Compare Players
# =============================================================================

@tool
def compare_players(
    context: Dict[str, Any],
    player_names: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compare multiple players side by side.
    
    Use this tool when the user asks:
    - "Compare John and Mike"
    - "How does player A compare to player B?"
    - "Side by side comparison"
    
    Args:
        context: Session context (injected automatically)
        player_names: Comma-separated list of player names to compare (e.g., "John, Mike, Sarah")
        start_date: Filter start date (YYYY-MM-DD)
        end_date: Filter end date (YYYY-MM-DD)
    
    Returns:
        Comparison of players' statistics
    """
    df = _get_df_from_context(context)
    
    # Parse player names
    names = [n.strip() for n in player_names.split(",")]
    
    # Match each player
    matched_players = []
    not_found = []
    for name in names:
        match = _fuzzy_match_player(df, name)
        if match:
            matched_players.append(match)
        else:
            not_found.append(name)
    
    if not matched_players:
        return {"error": "No matching players found", "not_found": not_found}
    
    # Apply date filter if provided
    if start_date and end_date:
        df = df[
            (df["date"] >= pd.to_datetime(start_date)) &
            (df["date"] <= pd.to_datetime(end_date))
        ]
    
    # Calculate stats for each player
    comparisons = []
    for player in matched_players:
        player_df = df[df["player_name"] == player]
        acwr = player_df["ACWR"].dropna()
        load = player_df["data"].dropna()
        
        latest = player_df.sort_values("date").iloc[-1] if not player_df.empty else None
        
        comparisons.append({
            "player": player,
            "records": len(player_df),
            "current_ACWR": round(float(latest["ACWR"]), 3) if latest is not None and pd.notna(latest["ACWR"]) else None,
            "current_category": latest.get("ACWR_category") if latest is not None else None,
            "mean_ACWR": round(float(acwr.mean()), 3) if not acwr.empty else None,
            "max_ACWR": round(float(acwr.max()), 3) if not acwr.empty else None,
            "mean_training_load": round(float(load.mean()), 1) if not load.empty else None,
        })
    
    logger.info(f"Compared {len(matched_players)} players")
    
    result = {"comparisons": comparisons}
    if not_found:
        result["not_found"] = not_found
    
    return result


# =============================================================================
# Tool 8: Get Team Trend
# =============================================================================

@tool
def get_team_trend(
    context: Dict[str, Any],
    start_date: str,
    end_date: str,
    aggregation: str = "daily",
) -> Dict[str, Any]:
    """
    Get team-wide ACWR trend over time.
    
    Use this tool when the user asks:
    - "Team average over time"
    - "How is the team doing overall?"
    - "Team trend this month"
    
    Args:
        context: Session context (injected automatically)
        start_date: Start date (YYYY-MM-DD) - required
        end_date: End date (YYYY-MM-DD) - required
        aggregation: "daily" or "weekly" (default "daily")
    
    Returns:
        Team average ACWR trend over the specified period
    """
    df = _get_df_from_context(context)
    
    # Filter by date
    df = df[
        (df["date"] >= pd.to_datetime(start_date)) &
        (df["date"] <= pd.to_datetime(end_date))
    ]
    
    if df.empty:
        return {"error": "No data in the specified date range"}
    
    # Aggregate
    if aggregation == "weekly":
        df["period"] = df["date"].dt.to_period("W").astype(str)
    else:
        df["period"] = df["date"].dt.strftime("%Y-%m-%d")
    
    trend = df.groupby("period").agg(
        mean_ACWR=("ACWR", "mean"),
        player_count=("player_name", "nunique"),
        high_risk_count=("ACWR_category", lambda x: (x == "high").sum()),
    ).round(3)
    
    trend_data = []
    for period, row in trend.iterrows():
        trend_data.append({
            "period": period,
            "mean_ACWR": float(row["mean_ACWR"]) if pd.notna(row["mean_ACWR"]) else None,
            "player_count": int(row["player_count"]),
            "high_risk_count": int(row["high_risk_count"]),
        })
    
    logger.info(f"Generated team trend: {len(trend_data)} periods")
    
    return {
        "date_range": {"start": start_date, "end": end_date},
        "aggregation": aggregation,
        "trend": trend_data,
    }


__all__ = [
    "get_data_summary",
    "get_player_data",
    "list_players",
    "get_high_risk_players",
    "get_undertraining_players",
    "get_player_rankings",
    "compare_players",
    "get_team_trend",
]
