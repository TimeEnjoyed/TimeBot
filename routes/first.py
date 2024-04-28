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
from typing import TYPE_CHECKING, Any

import twitchio
from starlette.responses import FileResponse, HTMLResponse

import core
from api import View, route


if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

    from api import Server

# this api endpoint just returns the longest streak (json) of a particular twitch user

logger: logging.Logger = logging.getLogger(__name__)


class Redeems(View):
    def __init__(self, app: Server) -> None:
        self.app = app

    #  (3/3 component- send new data)
    @route("/first/data", methods=["GET"])
    async def get_first_streak_data(self, request: Request) -> Response:
        all_redeems = await self.app.database.fetch_redeems()
        redeemer_twitch_id = all_redeems[0].twitch_id
        count = 0

        user_list: list[twitchio.User] = await self.app.tbot.fetch_users(ids=[redeemer_twitch_id])
        username: str = user_list[0].display_name

        for redeem in all_redeems:
            if redeemer_twitch_id != redeem.twitch_id:
                break
            count += 1

        html_data: str = f"""
            <span style="color: white; background-color: rgba(0, 0, 0, 0.3); font-size: 20px; font-decoration: bold; font-family: Montserrat, sans-serif; padding: 2px 5px 2px 5px; border-radius: 8px;">
                1st Streak: {username} ({count}x)!
            </span>
        """
        return HTMLResponse(html_data)

    # this path is redeems/first
    @route("/first", methods=["GET"])  # (2/3 component - displays the html page)
    async def get_first_streak(self, request: Request) -> Response:
        """this loads the index.html file at this path."""

        # return HTMLResponse(thing)
        return FileResponse("web/first-redeem/index.html")