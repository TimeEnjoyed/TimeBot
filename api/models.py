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
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import asyncpg


if TYPE_CHECKING:
    import datetime


__all__ = ("UserModel",)


class BaseModel(ABC):
    """Base model for all models, to serialize data (the dict) for API consumption."""

    @abstractmethod
    def as_dict(self) -> dict[str, Any]:
        raise NotImplementedError


class UserModel(BaseModel):
    def __init__(self, record: asyncpg.Record) -> None:
        self.uid: int = record["uid"]
        self.discord_id: int | None = record.get("discord_id", None)
        self.twitch_id: int | None = record.get("twitch_id", None)
        self.moderator: bool = record["moderator"]
        self.token: str = record["token"]
        self.created: datetime.datetime = record["created"]

    def as_dict(self) -> dict[str, Any]:
        return {
            "uid": self.uid,
            "discord_id": self.discord_id,
            "twitch_id": self.twitch_id,
            "moderator": self.moderator,
            "token": self.token,
            "created": self.created.isoformat(),
        }


class FirstRedeemModel(BaseModel):
    def __init__(self, record: asyncpg.Record) -> None:
        self.twitch_id: int = record["twitch_id"]
        self.timestamp: datetime.datetime = record["timestamp"]

    def as_dict(self) -> dict[str, Any]:
        return {
            "twitch_id": self.twitch_id,
            "timestamp": self.timestamp.isoformat(),
        }
