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
        player = wavelink.Pool.get_node().get_player(core.TIME_GUILD)

        if not player:
            return

        if not player.loaded:  # type: ignore
            return

        if player.loaded == player.current:  # type: ignore
            return

        await player.skip(force=True)
        await ctx.reply("Skipped the song.")

    @commands.command(aliases=["vol"])
    async def volume(self, ctx: commands.Context, *, value: str) -> None:
        if not ctx.author.is_mod:  # type: ignore
            return

        player: wavelink.Player | None
        player = wavelink.Pool.get_node().get_player(core.TIME_GUILD)

        if not player:
            return

        if not player.loaded:  # type: ignore
            return

        volume: int
        value = value.replace(" ", "")

        try:
            if value.startswith(("-", "+")):
                volume = max(5, min(player.volume + int(value), 50))
            else:
                volume = max(5, min(int(value), 50))
        except ValueError:
            await ctx.reply("Invalid volume passed.")
            return

        await player.set_volume(volume)
        await ctx.reply(f"Set the volume to {volume}")

    @commands.command()
    async def like(self, ctx: commands.Context) -> None:
        if not ctx.author.is_mod:  # type: ignore
            return

        player: wavelink.Player | None
        player = wavelink.Pool.get_node().get_player(core.TIME_GUILD)

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

            requester: twitchio.User | None = getattr(current, "twitch_user", None)

            if requester:
                await webhook.send(content=msg, avatar_url=requester.profile_image, username=requester.display_name)
            else:
                await webhook.send(content=msg, username="Bot AutoPlay")

        await ctx.reply("Sent this song to discord!")

    @commands.command(aliases=["nowplaying", "current", "currentsong", "song"])
    async def playing(self, ctx: commands.Context) -> None:
        player: wavelink.Player | None
        player = wavelink.Pool.get_node().get_player(core.TIME_GUILD)

        if not player:
            return

        if not player.loaded:  # type: ignore
            return

        if player.loaded == player.current:  # type: ignore
            await ctx.reply(f"Currently playing {player.current} by {player.current.author}.")  # type: ignore
            return

        if player.current:
            if not player.current.is_stream:
                time_ = f"{self.ms_to_hr(player.position)}/{self.ms_to_hr(player.current.length)}"
            elif player.current.is_stream:
                time_ = "Live Stream"

            current: wavelink.Playable = player.current

            requester: twitchio.User | None = getattr(current, "twitch_user", None)
            requested: str = f"@{requester.name}" if requester else "Bot AutoPlay"

            await ctx.reply(
                f"Currently playing {current} by {current.author} requested by: {requested} [{time_}]"  # type: ignore
            )

    @commands.command(aliases=["pause", "resume"])
    async def toggle(self, ctx: commands.Context) -> None:
        if not ctx.author.is_mod:  # type: ignore
            return

        player: wavelink.Player | None
        player = wavelink.Pool.get_node().get_player(core.TIME_GUILD)

        if not player:
            return

        if not player.loaded:  # type: ignore
            return

        await player.pause(not player.paused)

        if player.paused:
            await ctx.reply("Paused the player.")
        else:
            await ctx.reply("Resumed the player.")

    def ms_to_hr(self, milli: int) -> str:
        seconds: int = milli // 1000
        _, secs = divmod(seconds, 60)
        hours, mins = divmod(_, 60)

        return f"{hours}:{mins:02}:{secs:02}"

    @commands.command()
    async def player(self, ctx: commands.Context) -> None:
        if not ctx.author.is_mod:  # type: ignore
            return

        player: wavelink.Player | None
        player = wavelink.Pool.get_node().get_player(core.TIME_GUILD)

        if not player:
            await ctx.reply("There currently is no player connected.")
            return

        current: wavelink.Playable | None = player.current
        time_: str | None = None

        if current and not current.is_stream:
            time_ = f"{self.ms_to_hr(player.position)}/{self.ms_to_hr(current.length)}"
        elif current and current.is_stream:
            time_ = "Live Stream"

        try:
            requester: str = current.twitch_user.name  # type: ignore
        except AttributeError:
            requester: str = "Unknown"

        await ctx.reply(
            (
                f"Playing?: {player.playing}, "
                f"Paused: {player.paused}, "
                f"Volume: {player.volume}, "
                f"Ping: {player.ping}ms, "
                f"Current: {current}, "
                f"Position: {time_}, "
                f"Requester: {requester}, "
                f"AutoPlay: {player.autoplay}, "
                f"AutoQueue: {len(player.auto_queue)} "
            )
        )


def prepare(bot: core.TwitchBot) -> None:
    bot.add_cog(Music(bot))
