from logging import Logger
from typing import Annotated

from ascender.core import Controller, Inject

from common.link_models import LinkAnalysisResult, LinkClickEvent
from controllers.link_hooks import OnLinkOpen
from services.rickroll_firewall_service import RickrollFirewallService


@Controller(
    standalone=True,
    guards=[],
    imports=[],
    providers=[],
)
class LinkController:
    def __init__(
        self,
        firewall: RickrollFirewallService,
        logger: Annotated[Logger, Inject("ASC_LOGGER")],
    ) -> None:
        self._firewall = firewall
        self._logger = logger

    @OnLinkOpen(include_safe=False, include_blocked=True)
    async def intercept_links(self, event: LinkClickEvent, analysis: LinkAnalysisResult) -> None:
        if event.blocked:
            self._logger.info("Blocked Rickroll attempt from %s", event.url)
        else:
            self._logger.debug("Allowed link: %s (confidence %.2f)", event.url, analysis.confidence)