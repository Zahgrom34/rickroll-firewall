"""Shared data structures for link monitoring and analysis."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass(slots=True)
class LinkAnalysisResult:
    """Represents the outcome of link inspection."""

    is_rickroll: bool
    reason: str
    matched_pattern: Optional[str] = None
    confidence: float = 1.0


@dataclass(slots=True)
class LinkClickEvent:
    """Runtime event raised when the platform notices that a link was opened."""

    url: str
    source: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    blocked: bool = False
    blocked_by: Optional[str] = None
    block_reason: Optional[str] = None

    def block(self, *, reason: str, blocked_by: str) -> None:
        """Marks the event as blocked and annotates the metadata."""
        if self.blocked:
            return
        self.blocked = True
        self.block_reason = reason
        self.blocked_by = blocked_by
        self.metadata.setdefault("blocked_at", datetime.utcnow().isoformat(timespec="seconds"))


__all__ = ["LinkAnalysisResult", "LinkClickEvent"]
