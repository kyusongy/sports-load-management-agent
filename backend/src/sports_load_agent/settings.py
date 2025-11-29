"""
Application settings and configuration.

Reads from environment variables with sensible defaults.
Uses the same API endpoint pattern as Langgraph-DA (daagent env).
"""

import os
from pathlib import Path

# API Configuration - OpenAI Compatible Router
DEFAULT_API_ENDPOINT = "https://api.apiyi.com/v1"
DEFAULT_MODEL = "gpt-4.1"
DEFAULT_CHAT_MODEL = "claude-sonnet-4-5-20250929"

API_ENDPOINT = os.getenv("LANGGRAPH_API_ENDPOINT", DEFAULT_API_ENDPOINT)
API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL_NAME = os.getenv("LANGGRAPH_GENERAL_MODEL", DEFAULT_MODEL)

# Chat model for conversational tool calling (uses same API endpoint)
CHAT_MODEL = os.getenv("LANGGRAPH_CHAT_MODEL", DEFAULT_CHAT_MODEL)

# Path Configuration
BACKEND_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CACHE_DIR = BACKEND_ROOT / "runtime_cache"
UPLOADS_DIR = BACKEND_ROOT / "uploads"
OUTPUTS_DIR = BACKEND_ROOT / "outputs"

# Ensure directories exist
RUNTIME_CACHE_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# Server Configuration
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))

