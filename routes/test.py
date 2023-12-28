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

# from starlette.authentication import requires // for locking endpoints etc
from typing import TYPE_CHECKING, Any

import discord
from starlette.responses import JSONResponse, Response

from api import View, route

if TYPE_CHECKING:
    from starlette.requests import Request
    from api import Server

logger: logging.Logger = logging.getLogger(__name__)

MBTI_TYPES: list[str] = [
    "ESTP",
    "ESTJ",
    "ESFP",
    "ESFJ",
    "ISTP",
    "ISTJ",
    "ISFP",
    "ISFJ",
    "ENFJ",
    "ENTP",
    "ENFP",
    "ENTJ",
    "INTP",
    "INFJ",
    "INTJ",
    "INFP",
]
print(len(MBTI_TYPES))


class Test(View):
    def __init__(self, app: Server) -> None:
        self.app = app

    @route("/test", methods=["GET"])
    async def test_route(self, request: Request) -> Response:
        return Response(self.app.dbot.user.name, status_code=200)  # shows "TimeBot Test-Dec2023" in browser

    @route("/guilds", methods=["GET"])
    async def get_guild(self, request: Request) -> Response:
        return Response(
            self.app.dbot.get_guild(859565527343955998).get_member(402159684724719617).name, status_code=200
        )  # shows Mystypy  in browser

    @route("/roles", methods=["GET"])
    async def get_role(self, request: Request) -> Response:
        counts: dict[str, int] = self.app.dbot.mbti_count()
        return JSONResponse(counts, status_code=200)

    @route("/recursive", methods=["GET"])
    async def get_recursive(self, request: Request) -> Response:
        channel = self.app.tbot.get_channel("timeenjoyed")
        await channel.send("Hello from the API!")

        return Response(status_code=204)

    @route("/recursive_dbot", methods=["GET"])
    async def get_recursive_dbot(self, request: Request) -> Response:
        guild: discord.Guild = self.app.dbot.get_guild(859565527343955998)
        channel = guild.get_channel(1077565710391316561)
        await channel.send("Hello xD")
        return Response(status_code=204)

    @route("/discord_embed_test", methods=["GET"])
    async def discord_embed_test(self, request: Request) -> Response:
        guild: discord.Guild = self.app.dbot.get_guild(859565527343955998)
        channel = guild.get_channel(1077565710391316561)

        embed = discord.Embed(colour=0xFFC0CB, title="This is an embed")
        embed.description = "Hello from API rofl"
        embed.set_image(url="https://t4.ftcdn.net/jpg/05/51/22/65/360_F_551226555_JoynWcUCPb7U68psjX0PnNG51WF4to2E.jpg")
        await channel.send("test", embed=embed)
        return Response(status_code=204)


# GUILDS are objects
