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

from typing import TYPE_CHECKING, Any

import asyncpg


if TYPE_CHECKING:
    import datetime


__all__ = ("UserModel",)


class UserModel:
    def __init__(self, record: asyncpg.Record) -> None:
        self.uid: int = record["uid"]
        self.discord_id: int | None = record.get("discord_id", None)
        self.twitch_id: int | None = record.get("twitch_id", None)
        self.moderator: bool = record["moderator"]
        self.token: str = record["token"]
        self.created: datetime.datetime = record["created"]
        self.points: int = record["points"]

    def as_dict(self) -> dict[str, Any]:
        return {
            "uid": self.uid,
            "discord_id": self.discord_id,
            "twitch_id": self.twitch_id,
            "moderator": self.moderator,
            "token": self.token,
            "created": self.created.isoformat(),
            "points": self.points,
        }
