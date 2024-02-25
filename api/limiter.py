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

import datetime
import logging
from typing import TYPE_CHECKING, ClassVar


logger: logging.Logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from ..types_.limits import TatStore


class RateLimit:
    def __init__(self, rate: int, per: int) -> None:
        self.rate: int = rate
        self.period: datetime.timedelta = datetime.timedelta(seconds=per)

    @property
    def inverse(self) -> float:
        return self.period.total_seconds() / self.rate


class Store:
    __keys: ClassVar[dict[str, TatStore]] = {}

    @classmethod
    def get_tat(cls, key: str, /) -> datetime.datetime:
        now: datetime.datetime = datetime.datetime.now(tz=datetime.UTC)
        return cls.__keys.get(key, {"tat": now}).get("tat", now)

    @classmethod
    def set_tat(cls, key: str, /, *, tat: datetime.datetime, limit: RateLimit) -> None:
        cls.__keys[key] = {"tat": tat, "limit": limit}

    @classmethod
    def update(cls, key: str, limit: RateLimit) -> bool | float:
        now: datetime.datetime = datetime.datetime.now(tz=datetime.UTC)
        tat: datetime.datetime = max(cls.get_tat(key), now)

        # Clear stale keys...
        for ek, ev in cls.__keys.copy().items():
            if (now - ev["tat"]).total_seconds() > ev["limit"].period.total_seconds() + 60:
                del cls.__keys[ek]

        separation: float = (tat - now).total_seconds()
        max_interval: float = limit.period.total_seconds() - limit.inverse

        if separation > max_interval:
            return separation - max_interval

        new_tat: datetime.datetime = max(tat, now) + datetime.timedelta(seconds=limit.inverse)
        cls.set_tat(key, tat=new_tat, limit=limit)

        return False
