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

from starlette.responses import JSONResponse, Response

from api import View, route


if TYPE_CHECKING:
    from starlette.requests import Request

    from api import Server


logger: logging.Logger = logging.getLogger(__name__)



class Quotes(View):
    def __init__(self, app: Server) -> None:
        self.app = app

    @route("/{id}", methods=["GET"])
    async def fetch_quote(self, request: Request) -> Response:
        path: str = request.path_params.get("id", "")

        try:
            identifier: int = int(path)
        except ValueError:
            return Response("Bad quote ID.", status_code=400)

        row = await self.app.database.fetch_quote(identifier)
        if not row:
            return Response(f'Quote with id "{identifier}" was not found or may have been removed.', status_code=404)

        data: dict[str, Any] = {
            "id": identifier,
            "content": row["content"],
            "added_by": row["added_by"],
            "speaker": row["speaker"],
            "source": row["source"],
            "created": row["created"].isoformat()
        }

        return JSONResponse(data)
