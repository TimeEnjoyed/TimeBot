"""Copyright 2023 TimeEnjoyed <https://github.com/TimeEnjoyed/>, 2024 Mysty <https://github.com/EvieePy>

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

import base64
import datetime
import hashlib
import json
import logging
import secrets
from typing import TYPE_CHECKING, Any

import itsdangerous
import redis.asyncio as redis
from starlette.datastructures import MutableHeaders
from starlette.requests import HTTPConnection

from core import config


if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send


logger: logging.Logger = logging.getLogger(__name__)


class Storage:
    __slots__ = "pool"

    def __init__(self) -> None:
        rcfg = config["REDIS"]
        pool = redis.ConnectionPool.from_url(f"redis://{rcfg['host']}:{rcfg['port']}/{rcfg['db']}")  # type: ignore
        self.pool: redis.Redis = redis.Redis.from_pool(pool)

    async def get(self, data: dict[str, Any]) -> dict[str, Any]:
        expiry: datetime.datetime = datetime.datetime.fromisoformat(data["expiry"])
        key: str = data["_session_secret_key"]

        if expiry <= datetime.datetime.now():
            await self.pool.delete(key)  # type: ignore
            return {}

        session: Any = await self.pool.get(key)  # type: ignore
        return json.loads(session) if session else {}

    async def set(self, key: str, value: dict[str, Any], *, max_age: int) -> None:
        await self.pool.set(key, json.dumps(value), ex=max_age)  # type: ignore

    async def delete(self, key: str) -> None:
        await self.pool.delete(key)  # type: ignore


class SessionMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        name: str | None = None,
        secret: str | None = None,
        max_age: int | None = None,
        same_site: str = "lax",
        secure: bool = True,
    ) -> None:
        self.app: ASGIApp = app
        self.name: str = name or "__session_cookie"
        self.secret: str = secret or secrets.token_urlsafe(
            128
        )  # set this if you don't want to invalidate sessions on restart
        self.max_age: int = max_age or (60 * 60 * 24 * 7)  # 7 days; 1 week
        self.signing: itsdangerous.Signer = itsdangerous.Signer(self.secret, digest_method=hashlib.sha256)
        self.storage: Storage = Storage()

        self.flags: str = f"HttpOnly; SameSite={same_site}; Path=/{'; secure' if secure else ''}"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # Use this to cover both websocket connections and http connections
        connection: HTTPConnection = HTTPConnection(scope, receive)
        session: dict[str, Any]

        try:
            cookie: bytes = connection.cookies[self.name].encode("utf-8")
        except KeyError:
            cookie = b""

        try:
            unsigned: str = self.signing.unsign(base64.b64decode(cookie)).decode("utf-8")
            data: dict[str, Any] = json.loads(unsigned)
            session = await self.storage.get(data)
        except (KeyError, itsdangerous.BadSignature):
            session = {}

        original: dict[str, Any] = session.copy()
        scope["session"] = session

        async def wrapper(message: Message) -> None:
            if message["type"] != "http.response.start":
                await send(message)
                return

            headers: MutableHeaders = MutableHeaders(scope=message)
            secret_key: str = scope["session"].get("_session_secret_key", secrets.token_urlsafe(64))

            # At this point we can assume that the server has cleared the session...
            if not scope["session"] and original:
                await self.storage.delete(original["_session_secret_key"])
                headers.append("Set-Cookie", self.cookies(value="null", clear=True))

            # Server has updated the session data so we need to set a new cookie...
            elif scope["session"] != original:
                expiry = datetime.datetime.now() + datetime.timedelta(seconds=self.max_age)
                scope["session"]["_session_secret_key"] = secret_key

                cookie_: dict[str, str] = {"_session_secret_key": secret_key, "expiry": expiry.isoformat()}
                signed: bytes = base64.b64encode(self.signing.sign(json.dumps(cookie_)))
                headers.append("Set-Cookie", self.cookies(value=signed.decode("utf-8")))

                await self.storage.set(secret_key, scope["session"], max_age=self.max_age)

            elif not session and not original and cookie:
                headers.append("Set-Cookie", self.cookies(value="null", clear=True))

            await send(message)

        await self.app(scope, receive, wrapper)

    def cookies(self, *, value: str, clear: bool = False) -> str:
        if clear:
            return f"{self.name}={value}; {self.flags}; Max-Age=0"

        return f"{self.name}={value}; {self.flags}; Max-Age={self.max_age}"
