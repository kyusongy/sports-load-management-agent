"""
Report Generation Node for the sports load management workflow.

Uses LLM to generate interpretive report based on the processed data.
"""

from typing import Any, Dict

from loguru import logger

from sports_load_agent.agent_state import AgentState
from sports_load_agent.core.load_calculator import LoadCalculator
from sports_load_agent.utils.llm_factory import LLMFactory


def _generate_basic_report(stats: dict) -> str:
    """
    Generate a basic report without LLM when API is unavailable.

    Args:
        stats: Statistics dictionary from LoadCalculator.

    Returns:
        Markdown formatted basic report.
    """
    quality_dist = stats.get("load_quality_distribution", {})
    load_stats = stats.get("load_stats", {})
    high_players = stats.get("high_load_players", [])

    report = f"""# Training Load Analysis Report

## Summary

- **Total Records**: {stats.get("total_records", "N/A")}
- **Unique Players**: {stats.get("unique_players", "N/A")}
- **Date Range**: {stats.get("date_range", {}).get("start", "N/A")} to {stats.get("date_range", {}).get("end", "N/A")}
- **Missing Data Points**: {stats.get("missing_data_count", "N/A")}

## Load Quality Distribution

"""
    for quality, count in quality_dist.items():
        emoji = "🔴" if quality == "high" else ("🟡" if quality == "medium" else "🟢")
        report += f"- {emoji} **{quality.title()}**: {count} records\n"

    report += f"""
## ACWR Statistics

| Metric | Value |
|--------|-------|
| Mean | {load_stats.get("mean", "N/A")} |
| Median | {load_stats.get("median", "N/A")} |
| Min | {load_stats.get("min", "N/A")} |
| Max | {load_stats.get("max", "N/A")} |

## Athletes Requiring Attention

"""
    if high_players:
        report += "The following athletes have shown high load (ACWR > 1.5):\n\n"
        for player in high_players[:10]:
            report += f"- ⚠️ {player}\n"
        if len(high_players) > 10:
            report += f"\n... and {len(high_players) - 10} more athletes.\n"
    else:
        report += "No athletes currently showing elevated load risk.\n"

    report += """
## Recommendations

1. Monitor athletes with high ACWR values for signs of fatigue or injury
2. Consider reducing training intensity for high-risk athletes
3. Review training periodization for athletes with consistently elevated loads

---
*Note: This is an automated basic report. For detailed AI-powered analysis, please ensure the LLM API key is configured.*
"""
    return report


REPORT_PROMPT_TEMPLATE = """You are a sports science analyst specializing in training load management.

Analyze the following athlete training load data and provide a comprehensive report.

## Data Summary
- Total records: {total_records}
- Unique players: {unique_players}
- Date range: {date_start} to {date_end}
- Missing data points: {missing_count}

## Load Quality Distribution
{quality_distribution}

## Key Statistics
- Average ACWR (Load): {avg_load}
- Median ACWR: {median_load}
- Min ACWR: {min_load}
- Max ACWR: {max_load}

## Players with High Load (ACWR > 1.5)
{high_load_players}

## Your Task
Generate a professional report with the following sections:

1. **Executive Summary** (2-3 sentences)
   - Overall team training load status
   - Key concerns or positive observations

2. **Key Findings** (3-5 bullet points)
   - Specific observations about load distribution
   - Athletes requiring attention
   - Training load trends

3. **Risk Assessment**
   - Athletes at elevated injury risk (high ACWR)
   - Athletes potentially undertrained (low ACWR)

4. **Recommendations** (3-5 actionable items)
   - Specific guidance for coaching staff
   - Load management strategies

Format your response in Markdown.
"""


def report_generation_node(state: AgentState) -> Dict[str, Any]:
    """
    Report generation node that uses LLM to interpret results.

    Workflow:
    1. Load processed data statistics
    2. Build prompt with data summary
    3. Call LLM to generate interpretive report
    4. Save report as markdown

    Args:
        state: Current agent state with processed_data.

    Returns:
        State updates with report_markdown and final status.
    """
    logger.info("=== Report Generation Node ===")

    processed_data = state.get("processed_data")
    session_id = state.get("session_id", "unknown")

    if processed_data is None:
        logger.error("No processed data available")
        return {
            "status": "failed",
            "current_stage": "report_generation",
            "error_message": "No processed data available for report generation",
        }

    try:
        # Load DataFrame and calculate statistics
        df = processed_data.load(format="pandas")
        calculator = LoadCalculator(df)
        # Don't reprocess - just use existing columns
        stats = calculator.get_summary_stats()

        # Format quality distribution
        quality_dist = stats.get("load_quality_distribution", {})
        quality_str = "\n".join([f"- {k}: {v}" for k, v in quality_dist.items()])

        # Format high load players
        high_players = stats.get("high_load_players", [])
        high_players_str = (
            ", ".join(high_players[:10])
            if high_players
            else "None identified"
        )
        if len(high_players) > 10:
            high_players_str += f" (and {len(high_players) - 10} more)"

        # Build prompt
        load_stats = stats.get("load_stats", {})
        prompt = REPORT_PROMPT_TEMPLATE.format(
            total_records=stats.get("total_records", "N/A"),
            unique_players=stats.get("unique_players", "N/A"),
            date_start=stats.get("date_range", {}).get("start", "N/A"),
            date_end=stats.get("date_range", {}).get("end", "N/A"),
            missing_count=stats.get("missing_data_count", "N/A"),
            quality_distribution=quality_str or "No data",
            avg_load=load_stats.get("mean", "N/A"),
            median_load=load_stats.get("median", "N/A"),
            min_load=load_stats.get("min", "N/A"),
            max_load=load_stats.get("max", "N/A"),
            high_load_players=high_players_str,
        )

        # Call LLM
        logger.info("Generating report with LLM...")
        try:
            llm = LLMFactory.create_chat_model(
                temperature=0.3,
                session_id=session_id,
            )

            response = llm.invoke(prompt)
            report_markdown = response.content
            logger.info(f"Report generated: {len(report_markdown)} characters")
        except Exception as llm_error:
            logger.warning(f"LLM call failed: {llm_error}. Generating basic report.")
            # Generate a basic report without LLM
            report_markdown = _generate_basic_report(stats)

        # Get token stats
        token_stats = LLMFactory.get_session_stats(session_id) or {}

        return {
            "report_markdown": report_markdown,
            "token_usage": {
                "total_tokens": token_stats.get("total_tokens", 0),
                "prompt_tokens": token_stats.get("total_prompt_tokens", 0),
                "completion_tokens": token_stats.get("total_completion_tokens", 0),
            },
            "status": "completed",
            "current_stage": "report_generation",
            "error_message": None,
        }

    except Exception as e:
        logger.exception(f"Report generation failed: {e}")
        return {
            "status": "failed",
            "current_stage": "report_generation",
            "error_message": f"Report generation error: {str(e)}",
        }


__all__ = ["report_generation_node"]

