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

import datetime
import json
import logging
import secrets
from typing import Any, Literal, cast

import aiohttp
import discord
import twitchio
import wavelink
from discord.ext import commands

import core


logger: logging.Logger = logging.getLogger(__name__)


MAX_SONG_LEN: int = 360000  # 6 mins in Milliseconds...


class RequestView(discord.ui.View):
    message: discord.Message | discord.WebhookMessage

    def __init__(
        self,
        *,
        timeout: float | None = 300,
        data: dict[str, Any],
        cog: Music,
        player: core.Player,
        track: wavelink.Playable,
        request_id: str,
    ) -> None:
        super().__init__(timeout=timeout)

        self.data = data
        self.player = player
        self.track = track
        self.cog = cog
        self.request_id = request_id

        self.actioned: bool = False

    async def interaction_check(self, interaction: discord.Interaction[core.DiscordBot]) -> bool:
        member: discord.Member = interaction.user  # type: ignore

        if not member.guild_permissions.kick_members:
            return False

        if self.actioned or not self.player.approvals.get(self.request_id):
            self._disable_all_buttons()
            await self.message.edit(view=self)

            return False

        return True

    def _disable_all_buttons(self) -> None:
        for item in self.children:
            if isinstance(item, (discord.ui.Button, discord.ui.Select)):
                item.disabled = True

    async def on_timeout(self) -> None:
        if self.actioned:
            return

        self.actioned = True
        await self.player.remove_approval(self.request_id)

        self._disable_all_buttons()
        await self.message.edit(view=self)

        channel: twitchio.Channel = self.cog.bot.tbot.get_channel("timeenjoyed")  # type: ignore
        await channel.send(f"@{self.track.twitch_user.name} - Your song request was automatically accepted.")  # type: ignore
        if self.player.current == self.player.loaded:  # type: ignore
            await self.player.play(self.track, replace=True)
        else:
            self.player.queue.put(self.track)

        await self.cog.update_redemption(data=self.data, status="FULFILLED")

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction[core.DiscordBot], button: discord.ui.Button) -> None:
        await interaction.response.defer()

        if self.actioned:
            return

        self.actioned = True
        await self.player.remove_approval(self.request_id)

        channel: twitchio.Channel = interaction.client.tbot.get_channel("timeenjoyed")  # type: ignore
        await channel.send(f"@{self.track.twitch_user.name} - Your song request was accepted by a moderator.")  # type: ignore

        if self.player.current == self.player.loaded:  # type: ignore
            await self.player.play(self.track, replace=True)
        else:
            self.player.queue.put(self.track)

        await self.cog.update_redemption(data=self.data, status="FULFILLED")

        self._disable_all_buttons()
        await self.message.edit(view=self)

        self.stop()

    @discord.ui.button(label="Accept and Refund", style=discord.ButtonStyle.blurple)
    async def accept_refund(self, interaction: discord.Interaction[core.DiscordBot], button: discord.ui.Button) -> None:
        await interaction.response.defer()

        if self.actioned:
            return

        self.actioned = True
        await self.player.remove_approval(self.request_id)

        channel: twitchio.Channel = interaction.client.tbot.get_channel("timeenjoyed")  # type: ignore
        await channel.send(f"@{self.track.twitch_user.name} - Your song request was accepted by a moderator.")  # type: ignore

        if self.player.current == self.player.loaded:  # type: ignore
            await self.player.play(self.track, replace=True)
        else:
            self.player.queue.put(self.track)

        await self.cog.update_redemption(data=self.data, status="CANCELED")

        self._disable_all_buttons()
        await self.message.edit(view=self)

        self.stop()

    @discord.ui.button(label="Deny and Refund", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction[core.DiscordBot], button: discord.ui.Button) -> None:
        await interaction.response.defer()

        if self.actioned:
            return

        self.actioned = True
        await self.player.remove_approval(self.request_id)

        channel: twitchio.Channel = interaction.client.tbot.get_channel("timeenjoyed")  # type: ignore
        await channel.send(
            (
                f"@{self.track.twitch_user.name} - Your song request was rejected by a moderator."  # type: ignore
                "Your points were refunded."
            )
        )

        await self.cog.update_redemption(data=self.data, status="CANCELED")

        self._disable_all_buttons()
        await self.message.edit(view=self)

        self.stop()


class Music(commands.Cog):
    session: aiohttp.ClientSession

    def __init__(self, bot: core.DiscordBot) -> None:
        self.bot = bot

        # This event will technically come from our API server...
        self.bot.tbot.event_api_request_song = self.twitch_redemption  # type: ignore

    async def cog_load(self) -> None:
        self.session = aiohttp.ClientSession()

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload) -> None:
        player: core.Player | None = cast(core.Player, payload.player)
        if not player:
            return

        if player.autoplay is not wavelink.AutoPlayMode.disabled:
            return

        if payload.reason == "replaced":
            return

        loaded: wavelink.Playable | None = getattr(player, "loaded", None)
        if loaded:  # type: ignore
            try:
                track: wavelink.Playable = player.queue.get()
            except wavelink.QueueEmpty:
                await player.play(player.loaded)  # type: ignore
            else:
                await player.play(track)

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload) -> None:
        player: core.Player | None = cast(core.Player, payload.player)
        if not player:
            return

        await self.bot.server.dispatch_htmx("track_start", data={"player": player})

        loaded: wavelink.Playable | None = getattr(player, "loaded", None)
        if loaded and loaded == player.current:  # type: ignore
            return

        elif loaded and payload.original:  # type: ignore
            original: wavelink.Playable = payload.original

            requester: twitchio.User | None = getattr(original, "twitch_user", None)
            requested: str = f"@{requester.name}" if requester else "Bot AutoPlay"

            channel: twitchio.Channel = self.bot.tbot.get_channel("timeenjoyed")  # type: ignore
            await channel.send(f"Now Playing: {payload.track} requested by: {requested}")  # type: ignore
            return

        # At this point we are playing from Discord not Twitch...
        ...

    @commands.Cog.listener()
    async def on_wavelink_websocket_closed(self, payload: wavelink.WebsocketClosedEventPayload) -> None:
        await self.bot.server.dispatch_htmx("player_closed", data={"player": payload.player})

    @commands.Cog.listener()
    async def on_wavelink_inactive_player(self, player: wavelink.Player) -> None:
        await player.disconnect()

    async def update_redemption(self, data: dict[str, Any], *, status: Literal["CANCELED", "FULFILLED"]) -> None:
        # Temp setting for testing purposes...
        # status = "CANCELED"

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
            "Client-Id": json_["client_id"],
        }

        async with self.session.patch(url, json={"status": status}, headers=headers) as resp:
            if resp.status == 401:
                new: str | None = await self.bot.tbot.refresh_token(json_["refresh"])
                if not new:
                    return

                return await self.update_redemption(data=data, status=status)

            if resp.status != 200:
                body: str = await resp.text()
                logger.error("Failed to change redemption status: %s (Code: %s)", body, resp.status)
                return

            logger.info("Changed redemption status for <%s> to %s", redeem_id, status)

    async def twitch_redemption(self, data: dict[str, Any]) -> None:
        try:
            player: core.Player = cast(core.Player, self.bot.voice_clients[0])
        except IndexError:
            logger.warning("Unable to fulfill song request as the player is not connected.")
            return

        loaded: wavelink.Playable | None = getattr(player, "loaded", None)
        if not loaded:
            logger.warning("Unable to fulfill song request as the player is not currently loaded.")
            await self.update_redemption(data=data, status="CANCELED")
            return

        # user_id: str = data["user_id"]
        user_login: str = data["user_login"]
        user_input: str = data["user_input"]

        try:
            user: twitchio.User = (await self.bot.tbot.fetch_users(names=[user_login]))[0]
        except Exception:
            logger.warning("An error occurred fetching the user with name: %s. Unable to add song.", user_login)
            return await self.update_redemption(data=data, status="CANCELED")

        elevated: bool | None = False  # True == Moderator, None == VIP/Subscriber, False == Regular Viewer...
        channel: twitchio.Channel | None = self.bot.tbot.get_channel("timeenjoyed")
        if not channel:
            logging.warning("Unable to fulfill request as channel is not in cache.")
            return await self.update_redemption(data=data, status="CANCELED")

        else:
            chatter: twitchio.Chatter | twitchio.PartialChatter | None = channel.get_chatter(user_login)

            if chatter and chatter.is_mod:  # type: ignore
                elevated = True

            elif chatter and (chatter.is_subscriber or chatter.is_vip):  # type: ignore
                elevated = None

        try:
            tracks: wavelink.Search = await wavelink.Playable.search(user_input, source="ytmsearch")
        except wavelink.LavalinkLoadException as e:
            await channel.send(
                f"@{user_login} I was unable to request this song: {e.error}. Your points were refunded."
            )
            return await self.update_redemption(data=data, status="CANCELED")

        if not tracks:
            await channel.send(
                f"Sorry @{user_login} I was unable to find a song matching your request. I have refunded your points."
            )
            return await self.update_redemption(data=data, status="CANCELED")

        track: wavelink.Playable
        track = tracks[tracks.selected] if isinstance(tracks, wavelink.Playlist) else tracks[0]

        track.twitch_user = user  # type: ignore

        flags: list[str] = self.run_elevated_checks(track=track, player=player)

        if elevated or (elevated is None and not flags):
            if player.current == player.loaded:  # type: ignore
                await player.play(track, replace=True)
            else:
                player.queue.put(track)
                await channel.send(f"@{user_login} - Added the song {track} by {track.author} to the queue.")
                await self.bot.server.dispatch_htmx("player_update", data={"player": player})

            return await self.update_redemption(data=data, status="FULFILLED")

        embed: discord.Embed = discord.Embed(title="Stream Song Request", colour=0xFF888)
        embed.set_author(url=f"https://twitch.tv/{user_login}", name=user.display_name, icon_url=user.profile_image)
        embed.set_thumbnail(url=user.profile_image)
        embed.description = f"Requested the track: **`{track}`** by **`{track.author}`**"

        seconds, milliseconds = divmod(track.length, 1000)
        minutes, seconds = divmod(seconds, 60)

        embed.add_field(name="URL/Link", value=f"[Track URL]({track.uri})")
        embed.add_field(name="Service", value=f"**`{track.source}`**")
        embed.add_field(name="Duration", value=f"**`{minutes} minutes, {seconds} seconds`**")

        if flags:
            embed.add_field(name="Flags", value="\n".join(f"**`{f}`**" for f in flags))

        embed.set_image(url=track.artwork)

        id_: str = secrets.token_urlsafe(16)
        await player.add_approval(id_, {"id": id_, "data": data, "track": track})

        view: RequestView = RequestView(data=data, cog=self, player=player, track=track, request_id=id_)
        view.message = await player.channel.send(embed=embed, view=view)

    def run_elevated_checks(self, *, track: wavelink.Playable, player: core.Player) -> list[str]:
        flags: list[str] = []

        if track.length > MAX_SONG_LEN:
            flags.append("LONG TRACK DURATION")

        if track in player.queue.history:  # type: ignore
            flags.append("TRACK PREVIOUSLY REDEEMED")

        return flags

    @commands.hybrid_command()
    @commands.guild_only()
    @commands.has_guild_permissions(kick_members=True)
    async def stream_start(self, ctx: commands.Context, *, url: str) -> None:
        """Start the stream player.

        Parameters
        ----------
        url: str
            The URL of the continuous song to play.
        """
        await ctx.defer()

        player: core.Player
        player = cast(core.Player, ctx.voice_client)
        if player and not hasattr(player, "loaded"):
            await player.disconnect()
            player = None  # type: ignore

        if not player:
            try:
                player = await ctx.author.voice.channel.connect(cls=core.Player)  # type: ignore
                player.loaded = None  # type: ignore
            except discord.ClientException:
                await ctx.send("Please connect to a voice channel first!")
                return

        player.autoplay = wavelink.AutoPlayMode.enabled

        tracks: wavelink.Search = await wavelink.Playable.search(url)
        if not tracks:
            await ctx.send("Unable to find a track with that URL.")
            return

        track: wavelink.Playable = tracks[0]

        if not player.current or player.current == player.loaded:  # type: ignore
            if player.autoplay is wavelink.AutoPlayMode.enabled:
                logger.info("Starting Stream player with AutoPlay Enabled.")

                await player.queue.put_wait(track)
                await player.play(player.queue.get(), volume=20)
            else:
                await player.play(track, replace=True, volume=20)

        player.loaded = track  # type: ignore

        if not player.thread:
            assert ctx.guild is not None

            music_channel: discord.abc.GuildChannel | None = ctx.guild.get_channel(
                core.config["GENERAL"]["music_channel_id"]
            )

            if music_channel is not None and isinstance(music_channel, discord.TextChannel):
                date: str = datetime.datetime.now(tz=datetime.UTC).strftime("%Y-%m-%d %H")

                thread = await music_channel.create_thread(
                    name=f"Favourites {date}",
                    auto_archive_duration=1440,
                    reason="Stream Music Thread",
                )
                player.thread = thread

        await ctx.send("Successfully setup the stream player!")

    @commands.hybrid_command()
    @commands.guild_only()
    async def play(self, ctx: commands.Context, *, query: str) -> None:
        """Play a song with the given query."""
        player: core.Player

        if ctx.voice_client and hasattr(ctx.voice_client, "loaded"):
            await ctx.reply("I am unable to play songs currently as I am being used in stream!")
            return

        try:
            player = await ctx.author.voice.channel.connect(cls=core.Player)  # type: ignore
            await player.set_volume(30)
        except discord.ClientException:
            player = cast(core.Player, ctx.voice_client)
        except AttributeError:
            await ctx.send("Please join a voice channel first.")
            return

        if player.channel != ctx.channel:
            await ctx.send(f"Please request songs in {player.channel.mention}...")
            return

        player.autoplay = wavelink.AutoPlayMode.enabled

        tracks: wavelink.Search = await wavelink.Playable.search(query, source="spsearch:")
        if not tracks:
            await ctx.reply("Could not find any tracks with that query. Please try again.")
            return

        track: wavelink.Playable = tracks[0]
        track.extras = {"requester_id": ctx.author.id}

        await player.queue.put_wait(track)
        await ctx.reply(f"Added **`{track}`** to the queue.")

        if not player.playing:
            await player.play(player.queue.get())

        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

    @commands.hybrid_command(aliases=["dc", "stop"])
    @commands.guild_only()
    @commands.has_guild_permissions(kick_members=True)
    async def disconnect(self, ctx: commands.Context) -> None:
        """Disconnect the player and clear the state."""
        await ctx.defer()

        player: core.Player
        player = cast(core.Player, ctx.voice_client)

        if not player:
            await ctx.reply("I am not currently connected.")
            return

        await player.disconnect()
        await ctx.reply("Successfully disconnected the player.")

    @commands.hybrid_command(aliases=["vol"])
    @commands.guild_only()
    @commands.has_guild_permissions(kick_members=True)
    async def volume(self, ctx: commands.Context, *, value: commands.Range[int, 5, 50] = 20) -> None:
        """Set the volume of the player.

        Parameters
        ----------
        value: int
            A number between 5 and 50.
        """
        await ctx.defer()

        player: core.Player
        player = cast(core.Player, ctx.voice_client)

        if not player:
            await ctx.reply("I am not currently connected.")
            return

        await player.set_volume(value)
        await ctx.reply(f"Set the volume to **`{value}`**")

    @commands.hybrid_command(aliases=["pause", "resume"])
    @commands.guild_only()
    @commands.has_guild_permissions(kick_members=True)
    async def toggle(self, ctx: commands.Context) -> None:
        """Toggle the paused state of the player.

        If the player is currently paused this will resume the player.
        If the player is not currently paused, this will pause the player.
        """
        await ctx.defer()

        player: core.Player
        player = cast(core.Player, ctx.voice_client)

        if not player:
            await ctx.reply("I am not currently connected.")
            return

        await player.pause(not player.paused)

        if player.paused:
            await ctx.reply("Paused the player.")
        else:
            await ctx.reply("Resumed the player.")

    @commands.hybrid_command()
    @commands.guild_only()
    @commands.has_guild_permissions(kick_members=True)
    async def skip(self, ctx: commands.Context) -> None:
        """Skips the currently playing track."""
        await ctx.defer()

        player: core.Player
        player = cast(core.Player, ctx.voice_client)

        if not player:
            await ctx.reply("I am not currently connected.")
            return

        await player.skip(force=True)

    @commands.hybrid_command()
    @commands.guild_only()
    @commands.has_guild_permissions(kick_members=True)
    async def nightcore(self, ctx: commands.Context) -> None:
        """Apply the nightcore filter to the player."""
        player: core.Player = cast(core.Player, ctx.voice_client)
        if not player:
            return

        filters: wavelink.Filters = wavelink.Filters()
        filters.timescale.set(pitch=1.3, speed=1.3, rate=1)

        await player.set_filters(filters)
        await ctx.message.add_reaction("\u2705")

    @commands.hybrid_command()
    @commands.guild_only()
    @commands.has_guild_permissions(kick_members=True)
    async def no_filter(self, ctx: commands.Context) -> None:
        """Display any current filters applied to the player."""
        player: core.Player = cast(core.Player, ctx.voice_client)
        if not player:
            return

        await player.set_filters()
        await ctx.message.add_reaction("\u2705")

    @commands.hybrid_command()
    @commands.guild_only()
    async def current(self, ctx: commands.Context) -> None:
        """Display the currently playing song."""
        player: core.Player = cast(core.Player, ctx.voice_client)

        if not player or not player.current:
            await ctx.send("Not currently playing anything!")
            return

        message: str = f"Currently Playing: [{player.current.title}](<{player.current.uri}>)"
        await ctx.send(message)


async def setup(bot: core.DiscordBot) -> None:
    await bot.add_cog(Music(bot))
