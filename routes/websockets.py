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

import logging
import secrets
from typing import TYPE_CHECKING, Any

from starlette.authentication import requires
from starlette.websockets import WebSocket, WebSocketDisconnect

import api
import core
from api import View, limit, route


if TYPE_CHECKING:
    import asyncio

    from api import Server


logger: logging.Logger = logging.getLogger(__name__)


class Websockets(View):
    def __init__(self, app: Server) -> None:
        self.app = app
        self._keep_alives: list[asyncio.Task[None]] = []

    async def _keep_alive(self, uuid: str, *, websocket: WebSocket) -> None:
        await websocket.send_json({"op": api.WebsocketOPCodes.HELLO, "d": {"id": uuid}})

        while True:
            try:
                message: dict[str, Any] = await websocket.receive_json()
            except WebSocketDisconnect:
                logger.info('Websocket connection "%s" closed by remote.', uuid)
                return

            op: int | None = message.get("op")

            if op == api.WebsocketOPCodes.SUBSCRIBE:
                data: dict[str, Any] = message.get("d", {})
                subscription: str = data.get("subscription", "")

                if not data or not subscription:
                    logger.info("Received invalid subscribe message: %s", message)
                    await websocket.send_json(
                        {
                            "op": api.WebsocketOPCodes.NOTIFICATION,
                            "d": {"type": "error", "message": "Invalid subscription"},
                        },
                    )
                    continue

                self.app._websocket_listeners[uuid]["subscriptions"].add(subscription)
                await websocket.send_json(
                    {
                        "op": api.WebsocketOPCodes.NOTIFICATION,
                        "d": {"type": api.WebsocketNotificationTypes.SUBSCRIPTION_ADDED, "subscription": subscription},
                    },
                )

            elif op == api.WebsocketOPCodes.UNSUBSCRIBE:
                data: dict[str, Any] = message.get("d", {})
                subscription: str = data.get("subscription", "")

                if not data or not subscription:
                    logger.info("Received invalid unsubscribe message: %s", message)
                    await websocket.send_json(
                        {
                            "op": api.WebsocketOPCodes.NOTIFICATION,
                            "d": {"type": "error", "message": "Invalid subscription"},
                        },
                    )
                    continue

                self.app._websocket_listeners[uuid]["subscriptions"].discard(subscription)
                await websocket.send_json(
                    {
                        "op": api.WebsocketOPCodes.NOTIFICATION,
                        "d": {
                            "type": api.WebsocketNotificationTypes.SUBSCRIPTION_REMOVED,
                            "subscription": subscription,
                        },
                    },
                )

            else:
                logger.info("Received unknown OP from websocket: %s", uuid)

    @route("/connect", methods=["GET"], websocket=True)
    @requires("moderator")
    async def connect(self, websocket: WebSocket) -> None:
        # We use Authentication Middleware so we don't need to verify the user here...
        await websocket.accept()

        uuid: str = secrets.token_urlsafe(32)
        self.app._websocket_listeners[uuid] = {"websocket": websocket, "subscriptions": set()}

        try:
            await self._keep_alive(uuid, websocket=websocket)
        finally:
            del self.app._websocket_listeners[uuid]

        try:
            await websocket.close()
        except Exception as e:
            logger.debug(
                'Failed to close websocket connection "%s" gracefully: %s. It may have bee closed be remote.', uuid, e
            )

        logger.info('Websocket connection "%s" closed successfully.', uuid)
