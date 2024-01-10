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

import logging
import zoneinfo
from datetime import datetime

import asyncpg
import discord
import twitchio
from twitchio.ext import commands, routines

import core
from core.constants import TIMEZONES


STREAM_REFS_CHANNEL: int = core.config["GENERAL"]["stream_refs_id"]

logger: logging.Logger = logging.getLogger(__name__)


class General(commands.Cog):
    def __init__(self, bot: core.TwitchBot) -> None:
        self.bot = bot
        self.midnight.start()

    @commands.command(aliases=["ref"])  # type: ignore
    async def streamref(self, ctx: commands.Context) -> None:
        """Add a stream reference to the Discord channel via Twitch.
        Use this command when replying to a message.
        """
        if not ctx.author.is_mod:  # type: ignore
            return
        message: twitchio.Message = ctx.message

        reply: str | None = message.tags.get("reply-parent-msg-body", None)
        if not reply:
            return

        reply = reply.replace("\\s", " ")
        original_author: str = message.tags["reply-parent-display-name"]

        channel: discord.TextChannel = self.bot.dbot.get_channel(STREAM_REFS_CHANNEL)  # type: ignore
        name: str = ctx.author.display_name or ctx.author.name  # type: ignore

        msg: str = f"**{name}** added a reference from **{original_author}**:\n\n>>> {reply}\n\n"
        await channel.send(msg)

        await ctx.reply("Sent this reference to discord!")

    @commands.command()
    @commands.cooldown(1, 5, bucket=commands.Bucket.user)
    async def addquote(
        self, ctx: commands.Context, user_or: str | None = None, *, content_or: str | None = None
    ) -> None:
        """Add a quote by a specific user.

        Either mention the user or reply to a message.
        You must mention a user or reply for this command to work.
        """
        message: twitchio.Message = ctx.message
        content: str | None = content_or
        user_id: int | str | None = None

        reply: str | None = message.tags.get("reply-parent-msg-body", None)
        if reply:
            content = reply.replace("\\s", " ")
            user_id = message.tags["reply-parent-user-id"]

        elif not reply and (user_or and content):
            user_or = user_or.replace("@", "")
            user = ctx.channel.get_chatter(user_or)

            if not user:
                try:
                    user = (await self.bot.fetch_users(names=[str(user_or)]))[0]
                except IndexError:
                    pass
            else:
                user = await user.user()

            user_id = user.id if user else None  # type: ignore
        else:
            await ctx.reply(
                "Please enter a user to quote and their quote. Or reply to a users message with this command."
            )
            return

        try:
            row: asyncpg.Record = await self.bot.database.add_quote(
                content,
                added_by=ctx.author.id,  # type: ignore
                source="twitch",
                user=user_id,
            )
        except ValueError:
            await ctx.reply("Unable to add this quote as it already exists!")
            return

        await ctx.reply(f"Added the quote: {row['id']}")

    @commands.command()
    @commands.cooldown(1, 5, bucket=commands.Bucket.user)
    async def quote(self, ctx: commands.Context, *, name_or_id: int | str) -> None:
        quote: asyncpg.Record | None = None

        if isinstance(name_or_id, int):
            quote = await self.bot.database.fetch_quote(name_or_id)
        else:
            ...

        if not quote:
            await ctx.send(f"Could not find the quote with ID: {name_or_id}")
            return

        content: str = quote["content"].removeprefix('"').removesuffix('"')

        if not quote["speaker"]:
            await ctx.send(f'"{content}" - Unknown')
            return

        user: twitchio.User | discord.User | discord.Member | None = None
        if quote["source"] == "discord":
            guild: discord.Guild = self.bot.dbot.get_guild(859565527343955998)  # type: ignore
            user = guild.get_member(quote["speaker"]) or await self.bot.dbot.fetch_user(quote["speaker"])
        else:
            try:
                user = (await self.bot.fetch_users(ids=[quote["speaker"]], force=False))[0]
            except IndexError:
                pass

        await ctx.send(f'"{content}" - {user.name if user else "Unknown"}')

    @commands.command()
    async def http(self, ctx: commands.Context, *, code: str) -> None:
        status = core.status_codes.get(code, None)
        if not status:
            await ctx.reply(f'I could not find a statues code for "{code}"')
            return

        await ctx.reply(f"{status['name']} - {status['description']}")

    @commands.command()
    async def keyboard2(self, ctx: commands.Context) -> None:
        await ctx.reply("Logitech MX Mechanical Mini Wireless Illuminated Keyboard, Clicky Switches")

    @commands.command()
    async def count(self, ctx: commands.Context, mbti_type: str) -> None:
        data: dict[str, int] = self.bot.dbot.mbti_count()
        total: int | None = data.get(mbti_type.upper())

        if total is None:
            await ctx.reply(f"There are no {mbti_type} types in the server!")
            return

        await ctx.reply(f"There are {total} {mbti_type} types in the server!")

    @routines.routine(seconds=1)
    async def midnight(self) -> None:
        channel: twitchio.Channel | None = self.bot.get_channel("timeenjoyed")
        assert channel is not None

        for timezone in TIMEZONES:
            tz = zoneinfo.ZoneInfo(timezone)
            current = datetime.now(tz)

            if current.hour == 23 and current.minute == 47 and current.second == 0:
                logger.debug(f"The midnight Routine has detected it is {current} in {tz}")

                await channel.send(f"it's midnight in {timezone}!")


def prepare(bot: core.TwitchBot) -> None:
    bot.add_cog(General(bot))
