"""Copyright 2023 TimeEnjoyed <https://github.com/TimeEnjoyed/>

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
import secrets
from typing import TYPE_CHECKING, Any, ClassVar

from sse_starlette.sse import EventSourceResponse
from starlette.requests import Request
from starlette.responses import Response

import core
from api import View, limit, route


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from starlette.requests import Request

    from api import Server


logger: logging.Logger = logging.getLogger(__name__)


class SSE(View):
    VALID: ClassVar[set[str]] = {"track_start", "sent_song", "player_update"}

    def __init__(self, app: Server) -> None:
        self.app = app

    @route("/player", methods=["GET"])
    @limit(core.config["LIMITS"]["sse_player"]["rate"], core.config["LIMITS"]["sse_player"]["per"])
    async def music_player_sse(self, request: Request) -> EventSourceResponse | Response:
        forwarded: str | None = request.headers.get("X-Forwarded-For", None)
        ip: str = forwarded.split(",")[0] if forwarded else request.client.host  # type: ignore

        current: int = len([l for l in self.app.htmx_listeners if l.startswith(f"{ip}@")])
        if current >= 30:
            return Response("Too many SSE connections. Please close some existing connections.", status_code=429)

        id_: str = f"{ip}@{secrets.token_urlsafe(16)}"
        queue: asyncio.Queue = asyncio.Queue()
        self.app.htmx_listeners[id_] = queue

        logger.info('EventSource "%s" connection opened', id_)

        async def publisher() -> AsyncGenerator[dict[str, Any], Any]:
            try:
                while True:
                    data: dict[str, Any] = await queue.get()
                    event: str = data.get("event")

                    if not event:
                        logger.warning('EventSource "%s" received invalid event: %s', id_, event)
                        continue

                    event_data: dict[str, Any] = data.get("data", {})
                    if not event_data:
                        logger.warning('EventSource "%s" received invalid data: %s', id_, event_data)
                        continue

                    if event in self.VALID:
                        yield {"event": event, "data": ""}
                    else:
                        logger.warning('EventSource "%s" received invalid event: %s', id_, event)

            except asyncio.CancelledError as e:
                logger.info('EventSource "%s" connection closed: %s', id_, e)

                del self.app.htmx_listeners[id_]
                raise e

        return EventSourceResponse(publisher())
