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
import discord
from discord import app_commands
from discord.ext import commands

import core


_host: str = core.config["API"]["public_host"].removesuffix("/")
_prefix: str = core.config["API"]["prefix"].removeprefix("/").removesuffix("/")

REDIRECT: str = f"{_host}{'/' + _prefix if _prefix else ''}/oauth/twitch"
CLIENT_ID: str = core.config["TWITCH"]["client_id"]


class General(commands.Cog):
    def __init__(self, bot: core.DiscordBot) -> None:
        self.bot = bot

    @app_commands.command(name="link")
    @app_commands.checks.cooldown(1, 600)
    @app_commands.guild_only()
    async def link_accounts(self, interaction: discord.Interaction) -> None:
        """Links your discord and twitch accounts for this bot."""
        moderator: bool = interaction.user.guild_permissions.kick_members  # type: ignore
        state: str = await self.bot.database.create_state(discord_id=interaction.user.id, moderator=moderator)

        url: str = (
            "https://id.twitch.tv/oauth2/authorize"
            "?response_type=code"
            f"&client_id={CLIENT_ID}"
            f"&redirect_uri={REDIRECT}"
            "&force_verify=true"
            f"&state={state}"
        )

        if interaction.user == interaction.guild.owner:  # type: ignore
            url += "&scope=channel%3Aread%3Aredemptions+channel%3Amanage%3Aredemptions+moderator%3Amanage%3Ashoutouts"
        else:
            url += "&scope="

        await interaction.response.send_message(
            f"Please visit the URL below to update or create your link:\n\n[Twitch Authentication](<{url}>)",
            ephemeral=True,
        )


async def setup(bot: core.DiscordBot) -> None:
    await bot.add_cog(General(bot))
