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
from typing import Any

import discord
import wavelink


__all__ = ("Player",)


class Player(wavelink.Player):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.approvals: dict[str, dict[str, Any]] = {}
        self.thread: discord.Thread | None = None

    async def remove_approval(self, id_: str) -> None:
        self.approvals.pop(id_, None)
        await self.client.server.dispatch_htmx("player_update", data={"player": self})  # type: ignore

    async def add_approval(self, id_: str, data: dict[str, Any]) -> None:
        self.approvals[id_] = data
        await self.client.server.dispatch_htmx("player_update", data={"player": self})  # type: ignore

    def ms_to_hr(self, milli: int) -> str:
        seconds: int = milli // 1000
        _, secs = divmod(seconds, 60)
        hours, mins = divmod(_, 60)

        return f"{hours}:{mins:02}:{secs:02}"
