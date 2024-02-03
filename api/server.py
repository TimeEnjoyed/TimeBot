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

import logging
from typing import TYPE_CHECKING

from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.cors import CORSMiddleware

import core
from middleware import AuthBackend
from routes import *

from .core import Application, View


if TYPE_CHECKING:
    from database import Database

logger: logging.Logger = logging.getLogger(__name__)


class Server(Application):
    def __init__(self, *, database: Database, tbot: core.TwitchBot, dbot: core.DiscordBot) -> None:
        self.database = database
        self.tbot = tbot
        self.dbot = dbot

        views: list[View] = [
            OAuthView(self),
            QuotesView(self),
            EventSubView(self),
            MbtiView(self),
            PlayerView(self),
        ]
        middleware: list[Middleware] = [
            Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]),
            Middleware(AuthenticationMiddleware, backend=AuthBackend(self)),
        ]

        super().__init__(
            prefix=core.config["API"]["prefix"], views=views, middleware=middleware, on_startup=[self.on_ready]
        )

    async def on_ready(self) -> None:
        logger.info("API Server successfully started!")
