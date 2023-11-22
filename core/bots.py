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
import pathlib
from typing import TYPE_CHECKING

import discord
from discord.ext import commands
from twitchio.ext import commands as tcommands

from .config import config


if TYPE_CHECKING:
    from database import Database

logger: logging.Logger = logging.getLogger(__name__)


class DiscordBot(commands.Bot):
    tbot: TwitchBot

    def __init__(self, *, database: Database) -> None:
        self.database = database

        intents: discord.Intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.presences = True

        super().__init__(intents=intents, command_prefix=config["DISCORD"]["prefix"])

    async def on_ready(self) -> None:
        assert self.user
        logger.info(f"Logged into Discord as {self.user} | {self.user.id}")


class TwitchBot(tcommands.Bot):
    def __init__(self, *, dbot: DiscordBot, database: Database) -> None:
        self.dbot = dbot
        self.database = database

        config_ = config["TWITCH"]
        super().__init__(token=config_["token"], prefix=config_["prefix"], initial_channels=config_["channels"])

        self.loaded: bool = False

    async def event_ready(self) -> None:
        logger.info(f"Logged into Twitch IRC as {self.nick}")

        if not self.loaded:
            location = ("extensions/twitch", "extensions.twitch")
            extensions: list[str] = [f"{location[1]}.{f.stem}" for f in pathlib.Path(location[0]).glob("*.py")]

            for extension in extensions:
                self.load_module(extension)

            self.loaded = True
            logger.info("Loaded extensions for Twitch Bot.")
