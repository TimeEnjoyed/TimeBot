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
import asyncio
import logging

import discord
import uvicorn

import api
import core
from database import Database


async def main() -> None:
    discord.utils.setup_logging(level=logging.INFO)

    async with Database() as database, core.DiscordBot(database=database) as dbot:
        # Init the API Server...
        app: api.Server = api.Server(database=database)

        # Init and run the Twitch Bot in the background...
        tbot: core.TwitchBot = core.TwitchBot(dbot=dbot, database=database)
        dbot.tbot = tbot
        _: asyncio.Task = asyncio.create_task(tbot.start())

        # Init and run the Discord Bot in the background...
        _: asyncio.Task = asyncio.create_task(dbot.start(core.config["DISCORD"]["token"]))

        # Configure Uvicorn to run our API and keep the asyncio event loop running...
        config = uvicorn.Config(app, host="localhost", port=core.config["API"]["port"])
        server = uvicorn.Server(config)
        await server.serve()


asyncio.run(main())
