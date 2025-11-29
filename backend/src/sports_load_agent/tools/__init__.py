"""
Tools module for conversational sports load analysis.

Provides comprehensive tools for data querying, visualization, and custom analysis.
"""

from sports_load_agent.tools.data_query_tools import (
    get_data_summary,
    get_player_data,
    list_players,
    get_high_risk_players,
    get_undertraining_players,
    get_player_rankings,
    compare_players,
    get_team_trend,
)
from sports_load_agent.tools.visualization_tools import (
    plot_player_trend,
    plot_players_comparison,
    plot_team_timeline,
    plot_category_distribution,
    plot_rankings,
    plot_heatmap,
)
from sports_load_agent.tools.python_sandbox import (
    execute_python_analysis,
)

# All available tools
ALL_TOOLS = [
    # Data query tools (8)
    get_data_summary,
    get_player_data,
    list_players,
    get_high_risk_players,
    get_undertraining_players,
    get_player_rankings,
    compare_players,
    get_team_trend,
    # Visualization tools (6)
    plot_player_trend,
    plot_players_comparison,
    plot_team_timeline,
    plot_category_distribution,
    plot_rankings,
    plot_heatmap,
    # Fallback (1) - use as last resort
    execute_python_analysis,
]

__all__ = [
    # Data query tools
    "get_data_summary",
    "get_player_data",
    "list_players",
    "get_high_risk_players",
    "get_undertraining_players",
    "get_player_rankings",
    "compare_players",
    "get_team_trend",
    # Visualization tools
    "plot_player_trend",
    "plot_players_comparison",
    "plot_team_timeline",
    "plot_category_distribution",
    "plot_rankings",
    "plot_heatmap",
    # Fallback
    "execute_python_analysis",
    # All tools list
    "ALL_TOOLS",
]
