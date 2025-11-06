"""Custom controller hooks for responding to desktop link events."""
from __future__ import annotations

import inspect
from logging import Logger
from typing import Any, Awaitable, Callable, Optional

from ascender.core import ControllerDecoratorHook, inject

from common.link_models import LinkAnalysisResult, LinkClickEvent
from services.link_monitor_service import LinkMonitorService
from services.rickroll_firewall_service import RickrollFirewallService

class OnLinkOpen(ControllerDecoratorHook):
    """Controller hook that wires decorated methods to desktop link-open events."""

    def __init__(self, *, include_safe: bool = False, include_blocked: bool = True) -> None:
        super().__init__()
        self.include_safe = include_safe
        self.include_blocked = include_blocked
        self._subscription: Optional[str] = None
        self._logger: Optional[Logger] = None

    def on_load(self, callable: Callable[..., Awaitable[Any] | Any]) -> None:
        monitor = inject(LinkMonitorService)
        firewall = inject(RickrollFirewallService)
        self._logger = inject("ASC_LOGGER")
        monitor.ensure_running()

        async def handler(event: LinkClickEvent) -> None:
            analysis = await firewall.inspect(event)
            if not analysis.is_rickroll and not self.include_safe:
                return
            try:
                await _maybe_await(_invoke_controller_callback(callable, event, analysis))
            except Exception:  # pragma: no cover - defensive
                if self._logger:
                    self._logger.exception("Link hook handler failed for %s", callable)

        self._subscription = monitor.subscribe(
            handler,
            include_safe=self.include_safe,
            include_blocked=self.include_blocked,
        )


async def _maybe_await(result: Awaitable[Any] | Any) -> None:
    if inspect.isawaitable(result):
        await result  # pragma: no cover - trivial awaitable path


def _invoke_controller_callback(
    callback: Callable[..., Awaitable[Any] | Any],
    event: LinkClickEvent,
    analysis: LinkAnalysisResult,
) -> Awaitable[Any] | Any:
    signature = inspect.signature(callback)
    kwargs = {}
    positional = []

    for parameter in signature.parameters.values():
        if parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD):
            continue
        if parameter.name == "event":
            kwargs["event"] = event
        elif parameter.name == "analysis":
            kwargs["analysis"] = analysis

    if not kwargs:
        positional = [event, analysis]

    return callback(*positional, **kwargs)


__all__ = ["OnLinkOpen"]
