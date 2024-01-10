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

# from starlette.authentication import requires // for locking endpoints etc
from typing import TYPE_CHECKING

from starlette.responses import JSONResponse, Response

from api import View, route


if TYPE_CHECKING:
    from starlette.requests import Request

    from api import Server

logger: logging.Logger = logging.getLogger(__name__)


class Mbti(View):
    def __init__(self, app: Server) -> None:
        self.app = app

    @route("/roles", methods=["GET"])
    async def get_role(self, request: Request) -> Response:
        counts: dict[str, int] = self.app.dbot.mbti_count()
        return JSONResponse(counts, status_code=200)
