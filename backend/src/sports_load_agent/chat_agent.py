"""
Conversational chat agent for sports load analysis.

Uses Claude Sonnet 4.5 with tool calling to answer user queries about their
processed training load data.
"""

import functools
from typing import Any, Callable, Dict, List, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from loguru import logger

from sports_load_agent.settings import CHAT_MODEL
from sports_load_agent.utils.llm_factory import LLMFactory
from sports_load_agent.tools import ALL_TOOLS


SYSTEM_PROMPT = """You are a sports science analyst assistant specializing in training load management and injury prevention.

You help coaches and sports scientists analyze athlete training load data using the ACWR (Acute:Chronic Workload Ratio) methodology.

## Key Concepts
- **ACWR**: Ratio of short-term (acute, 3-day) to long-term (chronic, 2-week) training load
- **High ACWR (>1.5)**: Increased injury risk - athlete may be overloaded
- **Medium ACWR (0.67-1.5)**: Optimal training zone - appropriate load progression  
- **Low ACWR (<0.67)**: May indicate undertraining or detraining

## Dataset Columns
The processed data contains: player_name, date, data (training load), short_term_ave, long_term_ave, week_index, ACWR, ACWR_category

## Available Tools

### Data Query Tools (use these for data questions):
- `get_data_summary` - Overall statistics, player count, date range, ACWR distribution
- `get_player_data` - Individual player details and recent records
- `list_players` - List all players with current status
- `get_high_risk_players` - Players with high ACWR (injury risk)
- `get_undertraining_players` - Players with low ACWR (undertraining)
- `get_player_rankings` - Rank players by any metric
- `compare_players` - Side-by-side comparison of players
- `get_team_trend` - Team-wide ACWR trend over time

### Visualization Tools (use these for charts):
- `plot_player_trend` - Individual player ACWR over time
- `plot_players_comparison` - Multiple players on same chart
- `plot_team_timeline` - All players' trends
- `plot_category_distribution` - Pie chart of high/medium/low
- `plot_rankings` - Bar chart of top players
- `plot_heatmap` - Player x Time heatmap

### Fallback Tool (ONLY use as last resort):
- `execute_python_analysis` - Custom Python code for analysis not covered by other tools

## Guidelines
1. ALWAYS use the specific tools above before considering custom Python code
2. When users ask about dates, they must specify start_date and end_date (YYYY-MM-DD format)
3. Player names are fuzzy matched - partial names work
4. When generating visualizations, DO NOT mention file paths or download URLs - the chart will be displayed automatically
5. Provide clear, actionable insights that coaches can use
6. Be concise but thorough in your explanations
"""


def _create_context_injected_tool(tool_func: Callable, context: Dict[str, Any]) -> BaseTool:
    """
    Create a tool with context pre-injected.

    This wraps the original tool function to automatically inject the session context
    (containing processed_data, session_id, etc.) into every tool call.
    """
    original_tool = tool_func

    @functools.wraps(original_tool.func)
    def wrapper(**kwargs):
        kwargs["context"] = context
        return original_tool.func(**kwargs)

    new_tool = original_tool.copy()
    new_tool.func = wrapper

    # Update the schema to remove context parameter (it's injected)
    if hasattr(new_tool, "args_schema") and new_tool.args_schema:
        schema = new_tool.args_schema.schema()
        if "properties" in schema and "context" in schema["properties"]:
            del schema["properties"]["context"]
        if "required" in schema and "context" in schema["required"]:
            schema["required"].remove("context")

    return new_tool


def get_tools_with_context(context: Dict[str, Any]) -> List[BaseTool]:
    """
    Get all available tools with session context pre-injected.

    Args:
        context: Session context containing processed_data, session_id, etc.

    Returns:
        List of tools ready for use with the LLM
    """
    return [_create_context_injected_tool(tool, context) for tool in ALL_TOOLS]


class ChatAgent:
    """
    Conversational agent for sports load analysis.

    Uses Claude Sonnet 4.5 with tool calling to answer user queries.
    """

    def __init__(
        self,
        session_id: str,
        processed_data: Any,
        model: Optional[str] = None,
    ):
        """
        Initialize the chat agent.

        Args:
            session_id: Unique session identifier
            processed_data: DataFrameHandle containing processed data
            model: Model to use (defaults to CHAT_MODEL from settings)
        """
        self.session_id = session_id
        self.processed_data = processed_data
        self.model = model or CHAT_MODEL

        # Build context for tools
        self.context: Dict[str, Any] = {
            "session_id": session_id,
            "processed_data": processed_data,
            "generated_files": [],
        }

        # Initialize LLM
        self.llm = LLMFactory.create_chat_model(
            model=self.model,
            temperature=0.3,
            session_id=session_id,
        )

        # Get tools with context injected
        self.tools = get_tools_with_context(self.context)

        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # Conversation history
        self.messages: List[BaseMessage] = [
            SystemMessage(content=SYSTEM_PROMPT)
        ]

        logger.info(f"ChatAgent initialized for session {session_id} with {len(self.tools)} tools")

    def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """Execute a tool by name and return the result as a string."""
        for tool in self.tools:
            if tool.name == tool_name:
                try:
                    result = tool.invoke(tool_args)
                    return str(result)
                except Exception as e:
                    logger.error(f"Tool {tool_name} failed: {e}")
                    return f"Error executing {tool_name}: {str(e)}"

        return f"Tool '{tool_name}' not found"

    def chat(self, user_message: str) -> Dict[str, Any]:
        """
        Process a user message and return the agent's response.

        Implements a ReAct loop:
        1. Send user message to LLM with tools
        2. If LLM wants to use tools, execute them and send results back
        3. Repeat until LLM provides a final response

        Args:
            user_message: The user's question or request

        Returns:
            Dictionary with response text, tool calls made, and any generated files
        """
        logger.info(f"[{self.session_id}] User: {user_message[:100]}...")

        # Add user message to history
        self.messages.append(HumanMessage(content=user_message))

        tool_calls_made = []
        max_iterations = 10

        for iteration in range(max_iterations):
            # Call LLM
            response = self.llm_with_tools.invoke(self.messages)

            # Check if LLM wants to use tools
            if hasattr(response, "tool_calls") and response.tool_calls:
                self.messages.append(response)

                # Execute each tool call
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]

                    logger.info(f"[{self.session_id}] Tool: {tool_name}")
                    tool_result = self._execute_tool(tool_name, tool_args)

                    tool_calls_made.append({
                        "tool": tool_name,
                        "args": tool_args,
                        "result": tool_result,
                    })

                    # Add tool result to messages
                    from langchain_core.messages import ToolMessage
                    self.messages.append(
                        ToolMessage(
                            content=tool_result,
                            tool_call_id=tool_call["id"],
                        )
                    )

                continue

            # Final response
            self.messages.append(response)
            generated_files = self.context.get("generated_files", [])

            logger.info(f"[{self.session_id}] Done: {len(tool_calls_made)} tools, {len(generated_files)} files")

            return {
                "response": response.content,
                "tool_calls": tool_calls_made,
                "generated_files": generated_files,
            }

        # Max iterations reached
        logger.warning(f"[{self.session_id}] Max iterations reached")
        return {
            "response": "I encountered an issue processing your request. Please try rephrasing.",
            "tool_calls": tool_calls_made,
            "generated_files": self.context.get("generated_files", []),
            "error": "Max iterations reached",
        }

    def get_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history."""
        history = []
        for msg in self.messages:
            if isinstance(msg, SystemMessage):
                continue
            elif isinstance(msg, HumanMessage):
                history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                entry = {"role": "assistant", "content": msg.content}
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    entry["tool_calls"] = msg.tool_calls
                history.append(entry)
        return history

    def clear_history(self) -> None:
        """Clear conversation history (keeps system prompt)."""
        self.messages = [SystemMessage(content=SYSTEM_PROMPT)]
        self.context["generated_files"] = []
        logger.info(f"[{self.session_id}] History cleared")


# Session storage
_chat_agents: Dict[str, ChatAgent] = {}


def get_or_create_chat_agent(session_id: str, processed_data: Any) -> ChatAgent:
    """Get existing chat agent or create new one."""
    if session_id not in _chat_agents:
        _chat_agents[session_id] = ChatAgent(
            session_id=session_id,
            processed_data=processed_data,
        )
    return _chat_agents[session_id]


def remove_chat_agent(session_id: str) -> None:
    """Remove chat agent for a session."""
    if session_id in _chat_agents:
        del _chat_agents[session_id]
        logger.info(f"Removed chat agent: {session_id}")


__all__ = [
    "ChatAgent",
    "get_or_create_chat_agent",
    "remove_chat_agent",
]
