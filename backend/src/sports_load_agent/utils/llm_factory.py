"""
LLM Factory with Token Cost Tracking.

Centralizes all LLM initialization and tracks token usage across the application.
Ported from Langgraph-DA with adaptations for sports load agent.
"""

import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langchain.chat_models import init_chat_model
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from loguru import logger

from sports_load_agent.settings import API_ENDPOINT, MODEL_NAME


class TokenUsageTracker(BaseCallbackHandler):
    """
    Callback handler that tracks token usage from LLM responses.

    Thread-safe tracker that accumulates token statistics across all LLM calls.
    """

    def __init__(self, name: str = "global"):
        """
        Initialize token tracker.

        Args:
            name: Identifier for this tracker (e.g., "global", session_id)
        """
        super().__init__()
        self.name = name
        self.lock = threading.Lock()

        # Token counters
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0

        # Call statistics
        self.call_count = 0
        self.created_at = datetime.now(timezone.utc)
        self.last_updated_at = self.created_at

        # Per-model breakdown
        self.by_model: Dict[str, Dict[str, int]] = {}

        # Detailed token breakdowns
        self.total_cached_tokens = 0
        self.total_reasoning_tokens = 0

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """
        Track token usage when LLM call completes.

        Args:
            response: LLM response containing token usage metadata
            **kwargs: Additional callback arguments
        """
        if not response.llm_output or "token_usage" not in response.llm_output:
            return

        usage = response.llm_output["token_usage"]
        model_name = response.llm_output.get("model_name", "unknown")

        with self.lock:
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)

            self.total_prompt_tokens += prompt_tokens
            self.total_completion_tokens += completion_tokens
            self.total_tokens += total_tokens
            self.call_count += 1
            self.last_updated_at = datetime.now(timezone.utc)

            # Update per-model breakdown
            if model_name not in self.by_model:
                self.by_model[model_name] = {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "call_count": 0,
                }

            self.by_model[model_name]["prompt_tokens"] += prompt_tokens
            self.by_model[model_name]["completion_tokens"] += completion_tokens
            self.by_model[model_name]["total_tokens"] += total_tokens
            self.by_model[model_name]["call_count"] += 1

            # Track detailed breakdowns if available
            if "prompt_tokens_details" in usage:
                prompt_details = usage["prompt_tokens_details"]
                self.total_cached_tokens += prompt_details.get("cached_tokens", 0)

            if "completion_tokens_details" in usage:
                completion_details = usage["completion_tokens_details"]
                self.total_reasoning_tokens += completion_details.get(
                    "reasoning_tokens", 0
                )

            logger.debug(
                f"Token usage [{self.name}]: +{total_tokens} tokens "
                f"(prompt: {prompt_tokens}, completion: {completion_tokens}) "
                f"via {model_name}"
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get current token usage statistics."""
        with self.lock:
            return {
                "tracker_name": self.name,
                "total_prompt_tokens": self.total_prompt_tokens,
                "total_completion_tokens": self.total_completion_tokens,
                "total_tokens": self.total_tokens,
                "total_cached_tokens": self.total_cached_tokens,
                "total_reasoning_tokens": self.total_reasoning_tokens,
                "call_count": self.call_count,
                "created_at": self.created_at.isoformat(),
                "last_updated_at": self.last_updated_at.isoformat(),
                "by_model": dict(self.by_model),
            }

    def reset(self):
        """Reset all token counters and statistics."""
        with self.lock:
            self.total_prompt_tokens = 0
            self.total_completion_tokens = 0
            self.total_tokens = 0
            self.total_cached_tokens = 0
            self.total_reasoning_tokens = 0
            self.call_count = 0
            self.by_model.clear()
            self.created_at = datetime.now(timezone.utc)
            self.last_updated_at = self.created_at
            logger.info(f"Reset token tracker: {self.name}")


# Global token tracker instance
_global_tracker = TokenUsageTracker(name="global")

# Session-specific trackers
_session_trackers: Dict[str, TokenUsageTracker] = {}
_session_trackers_lock = threading.Lock()


class LLMFactory:
    """
    Factory for creating LLM instances with automatic token tracking.
    """

    @staticmethod
    def create_chat_model(
        model: Optional[str] = None,
        model_provider: str = "openai",
        base_url: Optional[str] = None,
        temperature: float = 0.0,
        session_id: Optional[str] = None,
        **kwargs,
    ):
        """
        Create a chat model with automatic token tracking.

        Args:
            model: Model name (default from settings)
            model_provider: Provider name (default: "openai")
            base_url: Optional base URL (default from settings)
            temperature: Model temperature (default: 0.0)
            session_id: Optional session ID for per-session tracking
            **kwargs: Additional arguments passed to init_chat_model

        Returns:
            Configured LLM instance with token tracking enabled
        """
        model = model or MODEL_NAME
        base_url = base_url or API_ENDPOINT

        llm = init_chat_model(
            model,
            model_provider=model_provider,
            base_url=base_url,
            temperature=temperature,
            **kwargs,
        )

        # Attach global tracker
        callbacks = [_global_tracker]

        # Optionally attach session-specific tracker
        if session_id:
            session_tracker = LLMFactory._get_or_create_session_tracker(session_id)
            callbacks.append(session_tracker)

        llm.callbacks = callbacks

        logger.debug(
            f"Created LLM: model={model}, provider={model_provider}, "
            f"temp={temperature}, session={session_id or 'none'}"
        )

        return llm

    @staticmethod
    def _get_or_create_session_tracker(session_id: str) -> TokenUsageTracker:
        """Get or create a session-specific token tracker."""
        with _session_trackers_lock:
            if session_id not in _session_trackers:
                _session_trackers[session_id] = TokenUsageTracker(
                    name=f"session:{session_id}"
                )
            return _session_trackers[session_id]

    @staticmethod
    def get_global_stats() -> Dict[str, Any]:
        """Get global token usage statistics."""
        return _global_tracker.get_stats()

    @staticmethod
    def get_session_stats(session_id: str) -> Optional[Dict[str, Any]]:
        """Get token usage statistics for a specific session."""
        with _session_trackers_lock:
            tracker = _session_trackers.get(session_id)
            return tracker.get_stats() if tracker else None

    @staticmethod
    def get_all_session_stats() -> List[Dict[str, Any]]:
        """Get token usage statistics for all tracked sessions."""
        with _session_trackers_lock:
            return [tracker.get_stats() for tracker in _session_trackers.values()]

    @staticmethod
    def reset_global_stats():
        """Reset global token usage statistics."""
        _global_tracker.reset()

    @staticmethod
    def reset_session_stats(session_id: str):
        """Reset token usage statistics for a specific session."""
        with _session_trackers_lock:
            tracker = _session_trackers.get(session_id)
            if tracker:
                tracker.reset()

    @staticmethod
    def clear_session_tracker(session_id: str):
        """Remove a session tracker completely."""
        with _session_trackers_lock:
            if session_id in _session_trackers:
                del _session_trackers[session_id]
                logger.info(f"Cleared session tracker: {session_id}")


def create_tracked_llm(
    model: Optional[str] = None,
    model_provider: str = "openai",
    base_url: Optional[str] = None,
    temperature: float = 0.0,
    session_id: Optional[str] = None,
    **kwargs,
):
    """
    Convenience function to create a tracked LLM instance.

    Shorthand for LLMFactory.create_chat_model().
    """
    return LLMFactory.create_chat_model(
        model=model,
        model_provider=model_provider,
        base_url=base_url,
        temperature=temperature,
        session_id=session_id,
        **kwargs,
    )


__all__ = [
    "LLMFactory",
    "TokenUsageTracker",
    "create_tracked_llm",
]

