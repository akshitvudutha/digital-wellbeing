"""Shared formatting helpers for elapsed durations displayed by Notch."""

from __future__ import annotations


def format_duration(seconds: float, *, compact: bool = False) -> str:
    """Format an elapsed duration without dropping non-zero seconds.

    Set ``compact=True`` for labels that omit zero-valued units while preserving
    any non-zero seconds remainder below one hour.
    """
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours:
        if compact and not minutes:
            return f"{hours}h"
        return f"{hours}h {minutes}m"
    if minutes:
        if compact and not secs:
            return f"{minutes}m"
        return f"{minutes}m {secs}s"
    return f"{secs}s"
