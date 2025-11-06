from typing import Sequence
from ascender.core.router import RouterRoute
from controllers.link_controller import LinkController
from controllers.main_controller import MainController


routes: Sequence[RouterRoute] = [
    {
        "path": "/link-monitor",
        "controller": LinkController,
        "tags": ["Link Monitor"],
        "include_in_schema": False
    },
]

__all__ = ["routes"]