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

import wavelink
from starlette.authentication import requires
from starlette.responses import JSONResponse, Response

import core
from api import View, limit, route


if TYPE_CHECKING:
    from starlette.requests import Request

    from api import Server

logger: logging.Logger = logging.getLogger(__name__)


class Player(View):
    def __init__(self, app: Server) -> None:
        self.app = app

    @route("/info", methods=["GET"])
    @limit(core.config["LIMITS"]["player_json"]["rate"], core.config["LIMITS"]["player_json"]["per"])
    async def get_player(self, request: Request) -> Response:
        player: wavelink.Player | None
        player = wavelink.Pool.get_node().get_player(core.TIME_GUILD)

        if not player:
            return JSONResponse({"error": "No player is currently active."}, status_code=404)

        try:
            no_track: bool = bool(int(request.query_params.get("no_track", 0)))
        except ValueError:
            no_track = True

        data: dict[str, Any] = {
            "volume": player.volume,
            "paused": player.paused,
            "position": player.position,
            "ping": player.ping,
            "queue": len(player.queue),
            "auto_queue": len(player.auto_queue),
            "current": player.current.raw_data if player.current and not no_track else None,
        }

        return JSONResponse(data, status_code=200)

    @route("/current", methods=["GET"])
    @limit(core.config["LIMITS"]["player_json"]["rate"], core.config["LIMITS"]["player_json"]["per"])
    async def get_current_track(self, request: Request) -> Response:
        player: wavelink.Player | None
        player = wavelink.Pool.get_node().get_player(core.TIME_GUILD)

        if not player:
            return JSONResponse({"error": "No player is currently active."}, status_code=404)

        if not player.current:
            return Response(status_code=204)

        return JSONResponse(player.current.raw_data, status_code=200)

    @route("/queue", methods=["GET"])
    @limit(core.config["LIMITS"]["player_json"]["rate"], core.config["LIMITS"]["player_json"]["per"])
    async def player_queue(self, request: Request) -> Response:
        player: wavelink.Player | None
        player = wavelink.Pool.get_node().get_player(core.TIME_GUILD)

        if not player:
            return JSONResponse({"error": "No player is currently active."}, status_code=404)

        queue = [track.raw_data for track in player.queue]
        auto_queue = [track.raw_data for track in player.auto_queue]

        data = {
            "queue": queue,
            "auto_queue": auto_queue,
        }
        return JSONResponse(data, status_code=200)

    @route("/controls/volume", methods=["PATCH"])
    @requires("moderator")
    async def set_player_volume(self, request: Request) -> Response:
        player: wavelink.Player | None
        player = wavelink.Pool.get_node().get_player(core.TIME_GUILD)

        if not player:
            return JSONResponse({"error": "No player is currently active."}, status_code=404)

        try:
            data: dict[str, Any] = await request.json()
        except Exception as e:
            logger.debug('Unable to parse JSON in ROUTE "player/controls/volume": %s', e, exc_info=True)
            return JSONResponse({"error": "Could not parse JSON."}, status_code=400)

        if not data:
            return JSONResponse({"error": "No data was provided."}, status_code=400)

        try:
            volume: int = int(data["volume"])
        except ValueError:
            return JSONResponse({"error": "Invalid volume value provided."}, status_code=400)
        except KeyError:
            return JSONResponse({"error": 'Missing the "volume" key.'}, status_code=400)

        new: int = max(5, min(volume, 100))
        old: int = player.volume
        await player.set_volume(new)

        to_return: dict[str, Any] = {
            "volume": new,
            "previous": old,
            "user": {
                "id": request.user.model.uid,
                "discord_id": request.user.model.discord_id,
                "twitch_id": request.user.model.twitch_id,
            },
        }

        self.app.tbot.run_event("api_player_volume", to_return)
        return JSONResponse(to_return, status_code=200)

    @route("/controls/pause", methods=["PATCH"])
    @requires("moderator")
    async def pause_player(self, request: Request) -> Response:
        player: wavelink.Player | None
        player = wavelink.Pool.get_node().get_player(core.TIME_GUILD)

        if not player:
            return JSONResponse({"error": "No player is currently active."}, status_code=404)

        await player.pause(not player.paused)

        to_return: dict[str, Any] = {
            "paused": player.paused,
            "user": {
                "id": request.user.model.uid,
                "discord_id": request.user.model.discord_id,
                "twitch_id": request.user.model.twitch_id,
            },
        }

        self.app.tbot.run_event("api_player_pause", to_return)
        return JSONResponse(to_return, status_code=200)

    @route("/controls/skip", methods=["PATCH"])
    @requires("moderator")
    async def skip_track(self, request: Request) -> Response:
        player: wavelink.Player | None
        player = wavelink.Pool.get_node().get_player(core.TIME_GUILD)

        if not player:
            return JSONResponse({"error": "No player is currently active."}, status_code=404)

        await player.skip(force=True)

        to_return: dict[str, Any] = {
            "user": {
                "id": request.user.model.uid,
                "discord_id": request.user.model.discord_id,
                "twitch_id": request.user.model.twitch_id,
            },
        }

        self.app.tbot.run_event("api_player_skip", to_return)
        return JSONResponse(to_return, status_code=200)

    @route("/controls/play", methods=["POST"])
    @requires("moderator")
    async def play_track(self, request: Request) -> Response:
        player: wavelink.Player | None
        player = wavelink.Pool.get_node().get_player(core.TIME_GUILD)

        if not player:
            return JSONResponse({"error": "No player is currently active."}, status_code=404)

        try:
            data: dict[str, Any] = await request.json()
        except Exception as e:
            logger.debug('Unable to parse JSON in ROUTE "player/controls/play": %s', e, exc_info=True)
            return JSONResponse({"error": "Could not parse JSON."}, status_code=400)

        if not data:
            return JSONResponse({"error": "No data was provided."}, status_code=400)

        try:
            search: str = str(data["track"])
        except KeyError:
            return JSONResponse({"error": 'Missing the "track" key.'}, status_code=400)

        tracks: wavelink.Search = await wavelink.Playable.search(search, source="ytmsearch")
        if not tracks:
            return JSONResponse({"error": f"No tracks were found with query: {search}."}, status_code=422)

        track: wavelink.Playable = tracks[0]
        player.queue.put(track)
        started: bool = False

        if not player.playing:
            started = True
            await player.play(player.queue.get())

        to_return: dict[str, Any] = {
            "track": track.raw_data,
            "started": started,
            "user": {
                "id": request.user.model.uid,
                "discord_id": request.user.model.discord_id,
                "twitch_id": request.user.model.twitch_id,
            },
        }

        self.app.tbot.run_event("api_player_play", to_return)
        return JSONResponse(to_return, status_code=200)
