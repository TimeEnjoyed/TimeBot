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
import json
import logging
from typing import Any, Literal, cast
from urllib.parse import quote

import aiohttp
import discord
import twitchio
import wavelink
from discord import app_commands
from discord.ext import commands

import core


logger: logging.Logger = logging.getLogger(__name__)


class Music(commands.Cog):
    session: aiohttp.ClientSession

    def __init__(self, bot: core.DiscordBot) -> None:
        self.bot = bot

        # This event will technically come from our API server...
        self.bot.tbot.event_api_request_song = self.twitch_redemption  # type: ignore

    async def cog_load(self) -> None:
        self.session = aiohttp.ClientSession()

    async def refresh_token(self, refresh: str) -> str | None:
        client_id: str = core.config["TWITCH"]["client_id"]
        client_secret: str = core.config["TWITCH"]["client_secret"]

        url = (
            "https://id.twitch.tv/oauth2/token?"
            "grant_type=refresh_token&"
            f"refresh_token={quote(refresh)}&"
            f"client_id={client_id}&"
            f"client_secret={client_secret}"
        )

        async with self.session.post(url) as resp:
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

    async def update_redemption(self, data: dict[str, Any], *, status: Literal["CANCELED", "FULFILLED"]) -> None:
        redeem_id: str = data["id"]
        reward_id: str = data["reward"]["id"]
        broadcaster_id: str = core.config["TIME_SUBS"]["twitch_id"]

        url = (
            f"https://api.twitch.tv/helix/channel_points/custom_rewards/redemptions?"
            f"id={redeem_id}&"
            f"broadcaster_id={broadcaster_id}&"
            f"reward_id={reward_id}"
        )

        # This kinda sucks, but due to the fact this can change when linking accounts, we need to re open the JSON...
        with open(".secrets.json") as fp:
            json_: dict[str, Any] = json.load(fp)

        headers: dict[str, str] = {
            "Authorization": f"Bearer {json_['token']}",
            "Client-Id": core.config["TWITCH"]["client_id"],
        }

        async with self.session.patch(url, json={"status": status}, headers=headers) as resp:
            if resp.status != 200:
                logger.error("Failed to change redemption status: %s (Code: %s)", resp.reason, resp.status)
                return

            if resp.status == 401:
                new: str | None = await self.refresh_token(json_["refresh"])
                if not new:
                    return

                return await self.update_redemption(data=data, status=status)

            logger.info("Changed redemption status for <%s> to %s", redeem_id, status)

    async def twitch_redemption(self, data: dict[str, Any]) -> None:
        try:
            player: wavelink.Player = cast(wavelink.Player, self.bot.voice_clients[0])
        except IndexError:
            logger.warning("Unable to fulfill song request as the player is not connected.")
            return

        # user_id: str = data["user_id"]
        user_login: str = data["user_login"]
        user_input: str = data["user_input"]

        try:
            user: twitchio.User = (await self.bot.tbot.fetch_users(names=[user_login]))[0]
        except Exception:
            logger.warning("An error occurred fetching the user with name: %s. Unable to add song.", user_login)
            return await self.update_redemption(data=data, status="CANCELED")

        elevated: bool = False
        channel: twitchio.Channel | None = self.bot.tbot.get_channel("timeenjoyed")
        if not channel:
            logging.warning("Unable to fulfill request as channel is not in cache.")
            return await self.update_redemption(data=data, status="CANCELED")

        else:
            chatter: twitchio.Chatter | twitchio.PartialChatter | None = channel.get_chatter(user_login)

            if chatter and (chatter.is_mod or chatter.is_subscriber or chatter.is_vip):  # type: ignore
                elevated = True

        tracks: wavelink.Search = await wavelink.Playable.search(user_input, source="ytmsearch")
        if not tracks:
            await channel.send(
                f"Sorry @{user_login} I was unable to find a song matching your request. I have refunded your points."
            )
            return await self.update_redemption(data=data, status="CANCELED")

        track: wavelink.Playable = tracks[0]
        track.twitch_user = user  # type: ignore

        if elevated:
            if player.queue:
                player.queue.put(track)
                await channel.send(f"@{user_login} - Added the song {track} by {track.author} to the queue.")
            else:
                await player.play(track)
                await channel.send(f"Now Playing: {track} requested by @{user_login}")

            return await self.update_redemption(data=data, status="FULFILLED")

        ...

    @commands.hybrid_command()
    @commands.guild_only()
    async def connect(self, ctx: commands.Context) -> None:
        player: wavelink.Player

        try:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player)  # type: ignore
        except discord.ClientException:
            player = cast(wavelink.Player, ctx.voice_client)
        except AttributeError:
            await ctx.send("Please connect to a voice channel first!")
            return

        await ctx.send(f"Connected: {player}")


async def setup(bot: core.DiscordBot) -> None:
    await bot.add_cog(Music(bot))
