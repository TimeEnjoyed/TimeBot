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

import json
import logging
from typing import TYPE_CHECKING

import aiohttp
from starlette.responses import Response

from api import View, limit, route
from core import config


if TYPE_CHECKING:
    from starlette.requests import Request

    from api import Server


logger: logging.Logger = logging.getLogger(__name__)


TWITCH_BASE: str = "https://id.twitch.tv/oauth2/token"
TWITCH_VALIDATE: str = "https://id.twitch.tv/oauth2/validate"

_host: str = config["API"]["public_host"].removesuffix("/")
_prefix: str = config["API"]["prefix"].removeprefix("/").removesuffix("/")

REDIRECT: str = f"{_host}{'/' + _prefix if _prefix else ''}/oauth/twitch"
CLIENT_ID: str = config["TWITCH"]["client_id"]
CLIENT_SECRET: str = config["TWITCH"]["client_secret"]


class OAuth(View):
    def __init__(self, app: Server) -> None:
        self.app = app

    @route("/twitch", methods=["GET"], prefix=True)
    @limit(config["LIMITS"]["twitch_auth"]["rate"], config["LIMITS"]["twitch_auth"]["per"])
    async def twitch_auth(self, request: Request) -> Response:
        params = request.query_params
        code: str | None = params.get("code", None)
        state: str | None = params.get("state", None)

        if not state:
            return Response("No state was provided.", status_code=400)

        if not code:
            return Response("Unable to Authenticate on Twitch.", status_code=400)

        url: str = (
            f"{TWITCH_BASE}?"
            f"client_id={CLIENT_ID}&"
            f"client_secret={CLIENT_SECRET}&"
            f"code={code}&"
            "grant_type=authorization_code&"
            f"redirect_uri={REDIRECT}"
        )

        async with aiohttp.ClientSession() as session:
            async with session.post(url) as resp:
                if resp.status != 200:
                    return Response(f"Twitch returned status (Auth): {resp.status}", status_code=500)

                data = await resp.json()
                access: str = data["access_token"]
                refresh: str = data["refresh_token"]

            async with session.get(TWITCH_VALIDATE, headers={"Authorization": f"OAuth {access}"}) as resp:
                if resp.status != 200:
                    return Response(f"Twitch returned status (Validate): {resp.status}", status_code=500)

                data = await resp.json()
                twitch_id: int = int(data["user_id"])
                client_id: str = data["client_id"]

        try:
            await self.app.database.refresh_or_create_user(twitch_id=twitch_id, state=state)
        except ValueError as e:
            return Response(f"Bad request: {e}", status_code=400)

        if twitch_id == int(config["TIME_SUBS"]["twitch_id"]):
            with open(".secrets.json", "r+") as fp:
                current: dict[str, str] = json.load(fp)

                current["token"] = access
                current["refresh"] = refresh
                current["client_id"] = client_id

                fp.seek(0)
                json.dump(current, fp=fp)
                fp.truncate()

        return Response("Success, you may close this window!", status_code=200)
