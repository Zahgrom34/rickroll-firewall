"""Rickroll detection and blocking services."""
from __future__ import annotations

from collections import deque
from logging import Logger
from typing import Annotated, Any, Dict

from ascender.common import Injectable
from ascender.core import Inject, Service

from common.link_models import LinkAnalysisResult, LinkClickEvent


@Injectable(provided_in="root")
class RickrollDetectorService(Service):
    """Small heuristic engine that flags Rick Astley bait links."""

    _PATTERNS: tuple[str, ...] = (
        "dQw4w9WgXcQ",
        "rickroll",
        "rick-roll",
        "never-gonna-give-you-up",
        "rick_astley",
        "youtu.be/dQw4w9WgXcQ",
        "youtube.com/watch?v=dQw4w9WgXcQ",
        "youtube.com/embed/dQw4w9WgXcQ",
        "tiktok.com/@rickastley",
    )

    async def analyze(self, url: str) -> LinkAnalysisResult:
        lower_url = url.lower()
        for pattern in self._PATTERNS:
            if pattern.lower() in lower_url:
                reason = f"Matched known Rickroll pattern: {pattern}"
                return LinkAnalysisResult(True, reason, matched_pattern=pattern)
        if any(token in lower_url for token in ("rick", "astley", "never gonna")):
            reason = "Matched heuristic keywords associated with Rick Astley"
            return LinkAnalysisResult(True, reason, matched_pattern="heuristic-keywords", confidence=0.7)
        return LinkAnalysisResult(False, "No Rickroll indicators detected", matched_pattern=None, confidence=0.1)


@Injectable(provided_in="root")
class RickrollFirewallService(Service):
    """Coordinates detection and blocking state for Rickroll attempts."""

    def __init__(
        self,
        detector: RickrollDetectorService,
        logger: Annotated[Logger, Inject("ASC_LOGGER")],
    ) -> None:
        self._detector = detector
        self._blocked: deque[Dict[str, Any]] = deque(maxlen=200)
        self._logger = logger

    async def inspect(self, event: LinkClickEvent) -> LinkAnalysisResult:
        cached = event.metadata.get("analysis")
        if isinstance(cached, LinkAnalysisResult):
            result = cached
        else:
            result = await self._detector.analyze(event.url)
            event.metadata["analysis"] = result
        if result.is_rickroll and not event.blocked:
            event.block(reason=result.reason, blocked_by=self.__class__.__name__)
            self._blocked.append(
                {
                    "url": event.url,
                    "when": event.timestamp.isoformat(timespec="seconds"),
                    "reason": result.reason,
                }
            )
            self._logger.warning("Blocked Rickroll attempt: %s", event.url)
        return result

    def history(self) -> list[Dict[str, Any]]:
        return list(self._blocked)


__all__ = [
    "RickrollDetectorService",
    "RickrollFirewallService",
]