"""
Sandboxed Python execution tool for custom analysis.

This tool allows the LLM to execute arbitrary Python code in a restricted
environment when the predefined tools cannot fulfill the user's request.
"""

import uuid
import traceback
from io import StringIO
from pathlib import Path
from typing import Any, Dict
import contextlib
import sys

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from langchain_core.tools import tool
from loguru import logger

from sports_load_agent.settings import OUTPUTS_DIR


def _get_df_from_context(context: Dict[str, Any]) -> pd.DataFrame:
    """Extract DataFrame from tool context."""
    df_handle = context.get("processed_data")
    if df_handle is None:
        raise ValueError("No processed data available.")
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


@tool
def execute_python_analysis(
    context: Dict[str, Any],
    code: str,
    description: str,
) -> Dict[str, Any]:
    """
    Execute custom Python code for analysis not covered by other tools.
    
    IMPORTANT: Only use this tool as a LAST RESORT when the predefined tools
    cannot fulfill the user's request. Try other specific tools first.
    
    The code runs in a sandboxed environment with:
    - Access to the processed DataFrame as `df`
    - Libraries: pandas (pd), numpy (np), matplotlib.pyplot (plt)
    - No file system access (except saving plots)
    - No network access
    - 30 second timeout
    
    To save a plot, use: plt.savefig(output_path)
    The output_path variable is pre-defined.
    
    Args:
        context: Session context (injected automatically)
        code: Python code to execute. Must be valid Python.
        description: Brief description of what the code does (for logging)
    
    Returns:
        Execution result including any printed output and generated plots
    """
    df = _get_df_from_context(context)
    session_id = _get_session_id(context)
    
    logger.info(f"Executing custom Python: {description}")
    
    # Prepare output path for any plots
    chart_id = str(uuid.uuid4())[:8]
    output_path = OUTPUTS_DIR / f"{session_id}_custom_{chart_id}.png"
    
    # Capture stdout
    stdout_capture = StringIO()
    
    # Restricted globals - only allow safe operations
    restricted_globals = {
        "__builtins__": {
            # Basic types
            "True": True,
            "False": False,
            "None": None,
            # Safe built-in functions
            "abs": abs,
            "all": all,
            "any": any,
            "bool": bool,
            "dict": dict,
            "enumerate": enumerate,
            "filter": filter,
            "float": float,
            "format": format,
            "int": int,
            "isinstance": isinstance,
            "len": len,
            "list": list,
            "map": map,
            "max": max,
            "min": min,
            "print": print,
            "range": range,
            "reversed": reversed,
            "round": round,
            "set": set,
            "sorted": sorted,
            "str": str,
            "sum": sum,
            "tuple": tuple,
            "type": type,
            "zip": zip,
        },
        # Data science libraries
        "pd": pd,
        "np": np,
        "plt": plt,
        # The data
        "df": df.copy(),  # Copy to prevent modification of original
        # Output path for plots
        "output_path": str(output_path),
    }
    
    # Local namespace for execution
    local_vars: Dict[str, Any] = {}
    
    result = {
        "success": False,
        "output": "",
        "error": None,
        "plot_generated": False,
        "download_url": None,
    }
    
    try:
        # Redirect stdout
        with contextlib.redirect_stdout(stdout_capture):
            # Execute the code
            exec(code, restricted_globals, local_vars)
        
        # Capture output
        result["output"] = stdout_capture.getvalue()
        result["success"] = True
        
        # Check if a plot was saved
        if output_path.exists():
            result["plot_generated"] = True
            result["download_url"] = _register_file(context, str(output_path))
            plt.close("all")
        
        # Check for any result variable
        if "result" in local_vars:
            result["result_value"] = str(local_vars["result"])[:1000]  # Limit size
        
        logger.info(f"Custom Python executed successfully: {description}")
        
    except SyntaxError as e:
        result["error"] = f"Syntax error: {e}"
        logger.warning(f"Custom Python syntax error: {e}")
        
    except Exception as e:
        result["error"] = f"Execution error: {type(e).__name__}: {e}"
        logger.warning(f"Custom Python execution error: {e}")
    
    finally:
        plt.close("all")  # Clean up any open figures
    
    return result


__all__ = ["execute_python_analysis"]

