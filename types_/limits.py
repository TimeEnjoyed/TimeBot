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

from collections.abc import Awaitable, Callable, Coroutine
from typing import TYPE_CHECKING, Any, Literal, TypeAlias, TypedDict

from starlette.requests import Request
from starlette.responses import Response
from starlette.websockets import WebSocket

from api.core import _Route


if TYPE_CHECKING:
    import datetime


__all__ = (
    "RateLimit",
    "ExemptCallable",
    "LimitDecorator",
    "T_LimitDecorator",
    "RateLimitData",
    "TatStore",
    "ResponseType",
)


ResponseType: TypeAlias = Coroutine[Any, Any, Response | None]


ExemptCallable: TypeAlias = Callable[[Request | WebSocket], Awaitable[bool]] | None
LimitDecorator: TypeAlias = Callable[[Any, Request], ResponseType] | _Route
T_LimitDecorator: TypeAlias = Callable[..., LimitDecorator]


class RateLimitData(TypedDict):
    rate: int
    per: int
    bucket: Literal["ip", "user"]
    exempt: ExemptCallable


class RateLimit(TypedDict):
    rate: int
    per: int


class TatStore(TypedDict):
    tat: datetime.datetime
    limit: Any
