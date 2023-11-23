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
import aiohttp
import discord
import twitchio
import wavelink
from twitchio.ext import commands

import core


class Music(commands.Cog):
    def __init__(self, bot: core.TwitchBot) -> None:
        self.bot = bot

        self.liked: list[str] = []

    @commands.command()
    async def skip(self, ctx: commands.Context) -> None:
        if not ctx.author.is_mod:  # type: ignore
            return

        player: wavelink.Player | None
        player = wavelink.Pool.get_node().get_player(859565527343955998)

        if not player:
            return

        if not player.loaded:  # type: ignore
            return

        if player.loaded == player.current:  # type: ignore
            return

        await player.skip(force=True)
        await ctx.reply("Skipped the song.")

    @commands.command(aliases=["vol"])
    async def volume(self, ctx: commands.Context, *, value: int) -> None:
        if not ctx.author.is_mod:  # type: ignore
            return

        player: wavelink.Player | None
        player = wavelink.Pool.get_node().get_player(859565527343955998)

        if not player:
            return

        if not player.loaded:  # type: ignore
            return

        volume: int = max(5, min(value, 50))

        await player.set_volume(volume)
        await ctx.reply(f"Set the volume to {volume}")

    @commands.command()
    async def like(self, ctx: commands.Context) -> None:
        if not ctx.author.is_mod:  # type: ignore
            return

        player: wavelink.Player | None
        player = wavelink.Pool.get_node().get_player(859565527343955998)

        if not player:
            return

        if not player.loaded:  # type: ignore
            return

        if player.current == player.loaded:  # type: ignore
            return

        current: wavelink.Playable | None = player.current
        if not current:
            return

        if current.identifier in self.liked:
            await ctx.reply("This song has already been liked!")
            return

        self.liked.append(current.identifier)
        msg: str = f"**{ctx.author.name}** liked a song from stream:\n{current.uri}"

        async with aiohttp.ClientSession() as session:
            url: str = core.config["GENERAL"]["music_webhook"]
            webhook: discord.Webhook = discord.Webhook.from_url(url=url, session=session)

            requester: twitchio.User = current.twitch_user  # type: ignore
            await webhook.send(content=msg, avatar_url=requester.profile_image, username=requester.display_name)

        await ctx.reply("Sent this song to discord!")

    @commands.command(aliases=["nowplaying", "current", "currentsong", "song"])
    async def playing(self, ctx: commands.Context) -> None:
        player: wavelink.Player | None
        player = wavelink.Pool.get_node().get_player(859565527343955998)

        if not player:
            return

        if not player.loaded:  # type: ignore
            return

        if player.loaded == player.current:  # type: ignore
            await ctx.reply(f"Currently playing {player.current}.")

        if player.current:
            await ctx.reply(f"Currently playing {player.current} requested by @{player.current.twitch_user.name}")  # type: ignore

    @commands.command(aliases=["pasue", "resume"])
    async def toggle(self, ctx: commands.Context) -> None:
        if not ctx.author.is_mod:  # type: ignore
            return

        player: wavelink.Player | None
        player = wavelink.Pool.get_node().get_player(859565527343955998)

        if not player:
            return

        if not player.loaded:  # type: ignore
            return

        if player.paused:
            await ctx.reply("Paused the player.")
        else:
            await ctx.reply("Resumed the player.")

    @commands.command()
    async def player(self, ctx: commands.Context) -> None:
        if not ctx.author.is_mod:  # type: ignore
            return

        player: wavelink.Player | None
        player = wavelink.Pool.get_node().get_player(859565527343955998)

        if not player:
            await ctx.reply("There currently is no player connected.")
            return

        await ctx.reply(
            f"Paused: {player.paused}, Volume: {player.volume}, Ping: {player.ping}, Current: {player.current}"
        )


def prepare(bot: core.TwitchBot) -> None:
    bot.add_cog(Music(bot))
