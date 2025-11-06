"""Link monitoring services for detecting suspicious link activity."""
from __future__ import annotations

import asyncio
import inspect
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from logging import Logger
from typing import Annotated, Awaitable, Callable, Dict, Iterable, List, Optional, Protocol

from ascender.common import Injectable
from ascender.core import Inject, Service

from common.link_models import LinkClickEvent


class LinkEventSource(Protocol):
    """Protocol implemented by classes capable of publishing link click events."""

    def start(self, loop: asyncio.AbstractEventLoop, monitor: "LinkMonitorService") -> None:
        ...


@dataclass(slots=True)
class _SubscriptionRecord:
    handler: Callable[[LinkClickEvent], Awaitable[None] | None]
    include_safe: bool
    include_blocked: bool


def _get_loop() -> asyncio.AbstractEventLoop:
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.get_event_loop()


async def _maybe_await(result: Awaitable[None] | None) -> None:
    if inspect.isawaitable(result):
        await result  # pragma: no cover - trivial awaitable path


@Injectable(provided_in="root")
class LinkMonitorService(Service):
    """Asynchronous dispatcher that subscribes to link events and relays them to handlers."""

    def __init__(
        self,
        recent_watcher: "DesktopRecentLinkWatcher",
        logger: Annotated[Logger, Inject("ASC_LOGGER")],
    ) -> None:
        self._handlers: Dict[str, _SubscriptionRecord] = {}
        self._queue: asyncio.Queue[LinkClickEvent] = asyncio.Queue()
        self._sources: List[LinkEventSource] = []
        self._sources_started: bool = False
        self._dispatch_task: Optional[asyncio.Task[None]] = None
        self._logger = logger
        self.register_source(recent_watcher)

    def register_source(self, source: LinkEventSource) -> None:
        self._sources.append(source)
        if self._sources_started:
            loop = _get_loop()
            source.start(loop, self)

    def subscribe(
        self,
        handler: Callable[[LinkClickEvent], Awaitable[None] | None],
        *,
        include_safe: bool = True,
        include_blocked: bool = True,
    ) -> str:
        token = f"sub-{id(handler):x}-{len(self._handlers)}"
        self._handlers[token] = _SubscriptionRecord(handler, include_safe, include_blocked)
        self.ensure_running()
        return token

    def unsubscribe(self, token: str) -> None:
        self._handlers.pop(token, None)

    async def publish(self, event: LinkClickEvent) -> None:
        await self._queue.put(event)

    def ensure_running(self) -> None:
        loop = _get_loop()
        if not self._dispatch_task or self._dispatch_task.done():
            self._dispatch_task = loop.create_task(self._dispatch_loop(), name="link-dispatch")
        if not self._sources_started:
            self._sources_started = True
            for source in self._sources:
                source.start(loop, self)

    async def _dispatch_loop(self) -> None:
        while True:
            event = await self._queue.get()
            for token, record in list(self._handlers.items()):
                if event.blocked and not record.include_blocked:
                    continue
                if not event.blocked and not record.include_safe:
                    continue
                try:
                    await _maybe_await(record.handler(event))
                except Exception:  # pragma: no cover - defensive
                    self._logger.exception("Unhandled exception in link handler %s", token)

    async def drain(self) -> None:
        while not self._queue.empty():
            await asyncio.sleep(0)


@Injectable(provided_in="root")
class DesktopRecentLinkWatcher(Service):
    """Polls the freedesktop recent files list and emits newly opened HTTP(S) links."""

    _NAMESPACE = "{http://www.freedesktop.org/standards/desktop-bookmarks}"

    def __init__(
        self,
        *,
        poll_interval: float = 1.0,
        recent_file: Optional[Path] = None,
        logger: Annotated[Logger, Inject("ASC_LOGGER")],
    ) -> None:
        self.poll_interval = poll_interval
        self.recent_file = recent_file or Path.home() / ".local/share/recently-used.xbel"
        self._processed: deque[str] = deque()
        self._processed_index: set[str] = set()
        self._window: int = 1024
        self._task: Optional[asyncio.Task[None]] = None
        self._monitor: Optional[LinkMonitorService] = None
        self._logger = logger

    def start(self, loop: asyncio.AbstractEventLoop, monitor: LinkMonitorService) -> None:
        if self._task and not self._task.done():
            return
        self._monitor = monitor
        self._task = loop.create_task(self._watch_loop(), name="recent-link-watcher")

    async def _watch_loop(self) -> None:
        while True:
            try:
                entries = await asyncio.to_thread(self._read_recent_entries)
                for event in entries:
                    if self._monitor:
                        await self._monitor.publish(event)
            except FileNotFoundError:
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:  # pragma: no cover - task shutdown
                raise
            except Exception:  # pragma: no cover - defensive
                self._logger.exception("Failed to read recent link entries")
            await asyncio.sleep(self.poll_interval)

    def _read_recent_entries(self) -> Iterable[LinkClickEvent]:
        import xml.etree.ElementTree as ET

        if not self.recent_file.exists():
            raise FileNotFoundError(self.recent_file)

        tree = ET.parse(self.recent_file)
        root = tree.getroot()
        namespace = {"bookmark": self._NAMESPACE.strip("{}")}
        for bookmark in root.findall("bookmark:bookmark", namespaces=namespace):
            href = bookmark.attrib.get("href", "")
            if not href.startswith("http"):
                continue
            visited = bookmark.attrib.get("visited") or bookmark.attrib.get("added") or ""
            entry_id = f"{href}|{visited}"
            if entry_id in self._processed_index:
                continue
            self._remember_entry(entry_id)
            metadata = {
                "added": bookmark.attrib.get("added"),
                "modified": bookmark.attrib.get("modified"),
                "visited": visited,
            }
            yield LinkClickEvent(url=href, source=str(self.recent_file), metadata=metadata)

    def _remember_entry(self, entry_id: str) -> None:
        self._processed.append(entry_id)
        self._processed_index.add(entry_id)
        while len(self._processed) > self._window:
            oldest = self._processed.popleft()
            self._processed_index.discard(oldest)


__all__ = [
    "LinkMonitorService",
    "DesktopRecentLinkWatcher",
]
