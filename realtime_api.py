"""Small realtime_api compatibility shim.

Provides `get_travel_insights_realtime(...)` so imports in `app.py` succeed
and the code can call a single entrypoint for realtime travel insights.

Behavior:
- If MISTRAL_API_KEY is set and `get_mistral_insights` is available, uses that.
- Otherwise falls back to `travel_planner.get_travel_recommendations`.
"""
from __future__ import annotations

import os
from typing import Optional

def get_travel_insights_realtime(destination: str, duration: str, budget: str, interests: str) -> str:
    """Return travel insights, preferring Mistral when configured.

    This shim prevents import errors in the app and centralizes the
    fallback behavior.
    """
    try:
        # Prefer Mistral-powered insights when an API key is present
        if os.getenv("MISTRAL_API_KEY"):
            from travel_planner_simple import get_mistral_insights
            return get_mistral_insights(destination, duration, budget, interests)
    except Exception:
        # Fall through to fallback implementation
        pass

    # Fallback: use the existing travel_planner instance
    try:
        from travel_planner_simple import travel_planner
        return travel_planner.get_travel_recommendations(
            f"{destination} ({duration}) — budget: {budget}; interests: {interests}"
        )
    except Exception as e:  # keep this broad to avoid breaking the app
        return f"No realtime insights available (fallback): {e}"

__all__ = ["get_travel_insights_realtime"]
