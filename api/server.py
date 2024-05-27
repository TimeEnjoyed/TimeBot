"""Copyright 2023 TimeEnjoyed <https://github.com/TimeEnjoyed/>, 2023 PythonistaGuild <https://github.com/PythonistaGuild>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles

import core
from middleware import AuthBackend
from routes import *

from .core import Application, View
from .sessions import SessionMiddleware


if TYPE_CHECKING:
    from database import Database

    from ..types_.websockets import WebsocketListener

logger: logging.Logger = logging.getLogger(__name__)


class Server(Application):
    def __init__(self, *, database: Database, tbot: core.TwitchBot, dbot: core.DiscordBot) -> None:
        self.database = database
        self.tbot = tbot
        self.dbot = dbot

        self.htmx_listeners: dict[str, asyncio.Queue] = {}
        self._websocket_listeners: dict[str, WebsocketListener] = {}

        views: list[View] = [
            OAuthView(self),
            QuotesView(self),
            EventSubView(self),
            MbtiView(self),
            PlayerView(self),
            PlayerDashboardView(self),
            SSEView(self),
            WebsocketsView(self),
            RedeemsView(self),
        ]
        middleware: list[Middleware] = [
            Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]),
            Middleware(AuthenticationMiddleware, backend=AuthBackend(self)),
            Middleware(SessionMiddleware, secret=core.config["API"]["secret"], max_age=core.config["API"]["max_age"]),
        ]

        super().__init__(
            prefix=core.config["API"]["prefix"],
            views=views,
            routes=[Mount("/static", app=StaticFiles(directory="web/static"), name="static")],
            middleware=middleware,
            on_startup=[self.on_ready],
        )

    async def on_ready(self) -> None:
        logger.info("API Server successfully started!")

    async def dispatch_htmx(self, event: str, *, data: dict[str, Any]) -> None:
        await asyncio.gather(*[queue.put({"event": event, "data": data}) for queue in self.htmx_listeners.values()])
