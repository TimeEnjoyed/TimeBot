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
import json
import logging
import pathlib
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import aiohttp
import discord
import twitchio
import wavelink
from discord.ext import commands
from twitchio.ext import commands as tcommands

from .config import config


if TYPE_CHECKING:
    from database import Database

logger: logging.Logger = logging.getLogger(__name__)


LIVE_ROLE_ID: int = 1182206699969458226
SUBBED_ROLE_ID: int = 873044115279990836


class DiscordBot(commands.Bot):
    tbot: TwitchBot

    def __init__(self, *, database: Database) -> None:
        self.database = database

        intents: discord.Intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.presences = True

        self.loaded: bool = False

        super().__init__(intents=intents, command_prefix=config["DISCORD"]["prefix"])

    async def on_ready(self) -> None:
        if self.loaded:
            return

        self.loaded = True

        assert self.user
        logger.info(f"Logged into Discord as {self.user} | {self.user.id}")

        guild: discord.Guild = self.get_guild(859565527343955998)  # type: ignore
        role: discord.Role = guild.get_role(LIVE_ROLE_ID)  # type: ignore
        subbed: discord.Role = guild.get_role(SUBBED_ROLE_ID)  # type: ignore

        for member in guild.members:
            if subbed not in member.roles:
                continue

            streaming = False

            for activity in member.activities:
                if isinstance(activity, discord.Streaming) and str(activity.platform).lower() == "twitch":
                    streaming = True

            if streaming and role not in member.roles:
                await member.add_roles(role)
                await asyncio.sleep(1)
            elif not streaming and role in member.roles:
                await member.remove_roles(role)
                await asyncio.sleep(1)

        logger.info("Finished updating roles in on_ready event.")

    async def setup_hook(self) -> None:
        node: wavelink.Node = wavelink.Node(uri=config["WAVELINK"]["uri"], password=config["WAVELINK"]["password"])
        await wavelink.Pool.connect(nodes=[node], client=self, cache_capacity=100)

        location = ("extensions/discord", "extensions.discord")
        extensions: list[str] = [f"{location[1]}.{f.stem}" for f in pathlib.Path(location[0]).glob("*.py")]

        for extension in extensions:
            await self.load_extension(extension)

        logger.info("Loaded extensions for Discord Bot.")

    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload) -> None:
        node: wavelink.Node = payload.node
        logger.info("Wavelink successfully connected: %s. Resumed: %s", node.identifier, payload.resumed)

    async def on_command_error(self, context: commands.Context, exception: commands.CommandError) -> None:
        if isinstance(exception, commands.CommandNotFound):
            return

        logger.exception(exception)

    async def on_presence_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.guild.id != 859565527343955998:
            return

        subbed: discord.Role | None = after.guild.get_role(SUBBED_ROLE_ID)
        if subbed not in after.roles:
            return

        bstream: discord.Streaming | None = None
        astream: discord.Streaming | None = None

        for activity in before.activities:
            if isinstance(activity, discord.Streaming) and str(activity.platform).lower() == "twitch":
                bstream = activity

        for activity in after.activities:
            if isinstance(activity, discord.Streaming) and str(activity.platform).lower() == "twitch":
                astream = activity

        if bstream is not None and astream is not None:
            return

        role: discord.Role = before.guild.get_role(LIVE_ROLE_ID)  # type: ignore

        if not bstream and astream and role not in before.roles:
            await before.add_roles(role, reason="Started streaming on Twitch")

        elif not astream and bstream and role in after.roles:
            await after.remove_roles(role, reason="Stopped streaming on Twitch")


class TwitchBot(tcommands.Bot):
    def __init__(self, *, dbot: DiscordBot, database: Database) -> None:
        self.dbot = dbot
        self.database = database

        config_ = config["TWITCH"]
        super().__init__(token=config_["token"], prefix=config_["prefix"], initial_channels=config_["channels"])

        self.loaded: bool = False

    async def refresh_token(self, refresh: str) -> str | None:
        client_id: str = config["TWITCH"]["client_id"]
        client_secret: str = config["TWITCH"]["client_secret"]

        url = (
            "https://id.twitch.tv/oauth2/token?"
            "grant_type=refresh_token&"
            f"refresh_token={quote(refresh)}&"
            f"client_id={client_id}&"
            f"client_secret={client_secret}"
        )

        async with aiohttp.ClientSession() as session:
            async with session.post(url) as resp:
                if resp.status != 200:
                    logger.warning("Unable to refresh token: %s", resp.status)
                    return None

                data: dict[str, Any] = await resp.json()
                access: str = data["access_token"]
                new_refresh: str = data["refresh_token"]

        with open(".secrets.json", "r+") as fp:
            current: dict[str, str] = json.load(fp)

            current["token"] = access
            current["refresh"] = new_refresh

            fp.seek(0)
            json.dump(current, fp=fp)
            fp.truncate()

        logger.info("Refreshed token successfully.")
        return new_refresh

    async def event_ready(self) -> None:
        logger.info(f"Logged into Twitch IRC as {self.nick}")

        if not self.loaded:
            location = ("extensions/twitch", "extensions.twitch")
            extensions: list[str] = [f"{location[1]}.{f.stem}" for f in pathlib.Path(location[0]).glob("*.py")]

            for extension in extensions:
                self.load_module(extension)

            self.loaded = True
            logger.info("Loaded extensions for Twitch Bot.")

    async def event_command_error(self, context: tcommands.Context, error: Exception) -> None:
        if isinstance(error, tcommands.CommandNotFound):
            return

        logger.exception(error)

    async def send_shoutout(self, payload: dict[str, str], refreshed: bool = False) -> None:
        # This kinda sucks, but due to the fact this can change when linking accounts, we need to re open the JSON...
        with open(".secrets.json") as fp:
            json_: dict[str, Any] = json.load(fp)

        headers: dict[str, str] = {
            "Authorization": f"Bearer {json_['token']}",
            "Client-Id": json_["client_id"],
        }

        url: str = "https://api.twitch.tv/helix/chat/shoutouts"
        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, json=payload, headers=headers) as resp:
                if resp.status == 401:
                    if refreshed:
                        logger.warning("Unable to send shoutout due to missing scopes.")
                        return

                    new: str | None = await self.refresh_token(json_["refresh"])
                    if new:
                        return await self.send_shoutout(payload=payload, refreshed=True)

                elif resp.status >= 300:
                    logger.warning("Unable to send shoutout: %s", resp.status)

    async def event_time_raid(self, from_id: str, viewers: int) -> None:
        users: list[twitchio.User] = await self.fetch_users(names=["timeenjoyed"])
        if not users:
            logger.warning("Unable to fetch TimeEnjoyed for raid notifications.")
            return

        time: twitchio.User = users[0]
        if not time.channel:
            logger.warning("Unable to fetch TimeEnjoyed from channel cache for raid notifications.")
            return

        raider: twitchio.ChannelInfo = await self.fetch_channel(broadcaster=from_id)
        if not raider:
            logger.warning("Unable to fetch raider for raid notifications.")
            return

        await time.channel.send(
            (
                f"timeenWave @{raider.user.name} just raided with {viewers} viewers timeenHug "
                f"they were streaming in {raider.game_name}!"
            )
        )

        payload: dict[str, str] = {
            "from_broadcaster_id": str(time.id),
            "to_broadcaster_id": str(from_id),
            "moderator_id": str(time.id),
        }
        await self.send_shoutout(payload=payload)
