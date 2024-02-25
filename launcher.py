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
import copy
import logging
from typing import Any

import aiohttp
import discord
import uvicorn

import api
import core
from database import Database
from types_.config import EventSubs


logger: logging.Logger = logging.getLogger(__name__)


USER_SUBS: list[EventSubs] = [core.config["TIME_SUBS"]]

PAYLOAD: dict[str, Any] = {
    "type": "...",
    "version": "1",
    "condition": {"broadcaster_user_id": "..."},
    "transport": {
        "method": "webhook",
        "callback": f"{core.config['API']['public_host'].removesuffix('/')}/eventsub/callback",
        "secret": core.config["TWITCH"]["eventsub_secret"],
    },
}


async def eventsub_subscribe() -> None:
    url = "https://api.twitch.tv/helix/eventsub/subscriptions"
    headers: dict[str, str] = {
        "Authorization": f"Bearer {core.config['TWITCH']['app_token']}",
        "Client-Id": core.config["TWITCH"]["client_id"],
    }

    payloads: list[dict[str, Any]] = []

    for user in USER_SUBS:
        if not user["events"]:
            continue

        for sub in user["events"]:
            payload: dict[str, Any] = copy.deepcopy(PAYLOAD)

            if sub == "channel.raid":
                payload["condition"] = {"to_broadcaster_user_id": user["twitch_id"]}
            else:
                payload["condition"]["broadcaster_user_id"] = user["twitch_id"]

            payload["type"] = sub
            payloads.append(payload)

    async with aiohttp.ClientSession() as session:
        for payload in payloads:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status >= 300:
                    logger.warning("EventSub subscription was not successful, status: %s", resp.status)
                    continue

                logger.info("Subscribed to EventSub: %s for %s", payload["type"], payload["condition"])


async def main() -> None:
    discord.utils.setup_logging(level=logging.INFO)

    async with Database() as database, core.DiscordBot(database=database) as dbot:
        # Init and run the Twitch Bot in the background...
        tbot: core.TwitchBot = core.TwitchBot(dbot=dbot, database=database)
        dbot.tbot = tbot
        _: asyncio.Task = asyncio.create_task(tbot.start())

        # Init and run the Discord Bot in the background...
        _: asyncio.Task = asyncio.create_task(dbot.start(core.config["DISCORD"]["token"]))

        # Init the API Server...
        app: api.Server = api.Server(database=database, tbot=tbot, dbot=dbot)
        dbot.server = app

        # Configure Uvicorn to run our API and keep the asyncio event loop running...
        config = uvicorn.Config(app, host="localhost", port=core.config["API"]["port"])
        server = uvicorn.Server(config)

        # Subscribe to our EventSub subscriptions...
        await eventsub_subscribe()

        # Start the API server and keep asyncio event loop running...
        await server.serve()


asyncio.run(main())
