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
import urllib.parse
from typing import TYPE_CHECKING, Any

import aiohttp
import discord
import twitchio
import wavelink
from markupsafe import escape
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response

import core
from api import View, limit, route


if TYPE_CHECKING:
    from starlette.requests import Request

    from api import Server, UserModel

logger: logging.Logger = logging.getLogger(__name__)


DISCORD_API_ENDPOINT = "https://discord.com/api/v10"
DISCORD_REDIRECT_URL: str = core.config["API"]["public_host"] + "playerdashboard/oauth/discord"
DISCORD_CDN_ENDPOINT: str = "https://cdn.discordapp.com/"


class PlayerDashboard(View):
    def __init__(self, app: Server) -> None:
        self.app = app

        self.liked: dict[int, list[str]] = {}
        self.sent: list[str] = []

    def get_badge_html(self, chatter: twitchio.Chatter) -> str:
        badges: list[str] = []

        if chatter.is_broadcaster:
            badges.append("https://static-cdn.jtvnw.net/badges/v1/5527c58c-fb7d-422d-b71b-f309dcb85cc1/2")

        if chatter.is_mod:
            badges.append("https://static-cdn.jtvnw.net/badges/v1/3267646d-33f0-4b17-b3df-f923a41db1d0/2")

        if chatter.is_vip:
            badges.append("https://static-cdn.jtvnw.net/badges/v1/b817aba4-fad8-49e2-b88a-7cc744dfa6ec/2")

        if chatter.is_turbo:
            badges.append("https://static-cdn.jtvnw.net/badges/v1/bd444ec6-8f34-4bf9-91f4-af1e3428d80f/2")

        return "\n".join([f'<img src="{badge}" />' for badge in badges])

    async def validate_discord_user(self, token: str) -> dict[str, Any] | None:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{DISCORD_API_ENDPOINT}/users/@me", headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                data = await resp.json()
                if resp.status != 200:
                    return None

        user_id: int = int(data.get("id", 0))
        if not user_id:
            return None

        guild: discord.Guild | None = self.app.dbot.get_guild(core.TIME_GUILD)
        if not guild:
            return None

        member: discord.Member | None = guild.get_member(user_id)
        if not member:
            return None

        if not any(r.id in core.config["DEBUG"]["access"] for r in member.roles):
            return None

        to_return: dict[str, Any] = {
            "id": user_id,
            "service": "discord",
            "avatar": f"{DISCORD_CDN_ENDPOINT}/avatars/{user_id}/{data['avatar']}.png",
            "name": data["username"],
            "moderator": False,
        }

        guild: discord.Guild | None = self.app.dbot.get_guild(core.TIME_GUILD)
        if not guild:
            return to_return

        member: discord.Member | None = guild.get_member(user_id)
        if not member:
            return to_return

        to_return["moderator"] = member.guild_permissions.kick_members
        return to_return

    @route("/login", methods=["GET"])
    @limit(core.config["LIMITS"]["player_login"]["rate"], core.config["LIMITS"]["player_login"]["per"])
    async def login(self, request: Request) -> Response:
        return FileResponse("web/player/login.html")

    @route("/login/redirect", methods=["GET"])
    @limit(core.config["LIMITS"]["player_login"]["rate"], core.config["LIMITS"]["player_login"]["per"])
    async def login_redirect(self, request: Request) -> Response:
        service: str | None = request.query_params.get("service", None)
        if not service:
            return RedirectResponse(url="/playerdashboard/login")

        if service == "discord":
            client_id: str = core.config["DISCORD"]["client_id"]
            redirect_uri: str = DISCORD_REDIRECT_URL
            url: str = (
                f"https://discord.com/api/oauth2/authorize"
                f"?client_id={client_id}"
                "&response_type=code"
                f"&redirect_uri={redirect_uri}"
                "&scope=identify"
            )
        elif service == "twitch":
            return Response("Twitch OAuth is not yet implemented.", status_code=400)
        else:
            return Response("Invalid Service", status_code=400)

        return RedirectResponse(url=url, status_code=307)

    @route("/logout", methods=["GET"])
    async def logout(self, request: Request) -> Response:
        request.session.clear()
        return RedirectResponse(url="/playerdashboard/login")

    @route("/oauth/twitch", methods=["GET"])
    async def oauth_twitch(self, request: Request) -> Response:
        ...

    @route("/oauth/discord", methods=["GET"])
    @limit(core.config["LIMITS"]["player_oauth"]["rate"], core.config["LIMITS"]["player_oauth"]["per"])
    async def oauth_discord(self, request: Request) -> Response:
        if request.session:
            return RedirectResponse(url="/music", status_code=307)

        params = request.query_params
        code: str | None = params.get("code", None)
        # state: str | None = params.get("state", None)

        if not code:
            return Response("Unable to Authenticate on Discord. Try again!", status_code=400)

        exchange: dict[str, Any] = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": DISCORD_REDIRECT_URL,
        }

        headers: dict[str, str] = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        client_id: str = core.config["DISCORD"]["client_id"]
        client_secret: str = core.config["DISCORD"]["client_secret"]
        credentials: aiohttp.BasicAuth = aiohttp.BasicAuth(client_id, client_secret)

        url: str = f"{DISCORD_API_ENDPOINT}/oauth2/token"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=exchange, headers=headers, auth=credentials) as resp:
                data = await resp.json()

                if resp.status != 200:
                    return JSONResponse({"error": f"Invalid response from Discord: {data}"}, status_code=resp.status)

                token: str = data.get("access_token", None)
                if not token:
                    return JSONResponse({"error": "Invalid token provided."}, status_code=400)

                user: dict[str, Any] | None = await self.validate_discord_user(token)
                if not user:
                    return JSONResponse({"error": "Unable to verify discord user."}, status_code=400)

        api_user: UserModel = await self.app.database.create_user(discord_id=user["id"], moderator=user["moderator"])
        request.session.update(
            {
                "token_": api_user.token,
                "service": "discord",
                "id": user["id"],
                "avatar": user["avatar"],
                "name": user["name"],
                "moderator": user["moderator"] or api_user.moderator,
            }
        )

        return RedirectResponse(url="/music", status_code=307)

    @route("/music", methods=["GET"], prefix=False)
    @limit(core.config["LIMITS"]["player_dashboard"]["rate"], core.config["LIMITS"]["player_dashboard"]["per"])
    async def player_dashboard(self, request: Request) -> Response:
        token: str = request.session.get("token_", "")

        if not token:
            return RedirectResponse(url="/playerdashboard/login")

        user: UserModel | None = await self.app.database.fetch_user(token)
        if not user:
            return RedirectResponse(url="/playerdashboard/login")

        return FileResponse("web/player/index.html")

    @route("/artwork", methods=["GET"])
    async def get_artwork(self, request: Request) -> Response:
        session: dict[str, Any] = request.session
        if not session:
            return HTMLResponse("""<a href="/playerdashboard/login">Login</a>""")

        player: core.Player | None
        player = wavelink.Pool.get_node().get_player(core.TIME_GUILD)  # type: ignore

        if not player or not hasattr(player, "loaded") or not player.current:
            html = """<img src="/static/img/album_placeholder.png" alt="Album Artwork" />"""
        else:
            html = f"""<img src="{player.current.artwork}" alt="Album Artwork" />"""

        return HTMLResponse(html)

    @route("/queue", methods=["GET"])
    @limit(core.config["LIMITS"]["player_queues"]["rate"], core.config["LIMITS"]["player_queues"]["per"])
    async def get_player_queue(self, request: Request) -> Response:
        session: dict[str, Any] = request.session
        if not session:
            return HTMLResponse("""<a href="/playerdashboard/login">Login</a>""")

        player: core.Player | None
        player = wavelink.Pool.get_node().get_player(core.TIME_GUILD)  # type: ignore

        if not player or not hasattr(player, "loaded"):
            html = """<b>No player is currently active.</b>"""
            return HTMLResponse(html)

        track_html: list[str] = []

        queues = list(player.queue.copy()) + player.auto_queue[0:10]
        for track in queues:
            artwork = track.artwork or "/static/img/album_placeholder.png"
            title = f"{escape(track.title)[:40]}{'...' if len(track.title) > 40 else ''}"
            author = f"{escape(track.author)[:40]}{'...' if len(track.author) > 40 else ''}"
            duration = track.length

            requester: twitchio.User | None = getattr(track, "twitch_user", None)
            requested: str = f"{requester.display_name}" if requester else "Bot AutoPlay"
            requester_url: str = f"https://twitch.tv/{requester.name}" if requester else "https://twitch.tv/thetimebot"
            requester_img: str = requester.profile_image if requester else "/static/img/time_bot.png"

            badge_html: str = ""
            channel: twitchio.Channel | None = self.app.tbot.get_channel("timeenjoyed")
            if requester and channel:
                chatter: twitchio.Chatter | twitchio.PartialChatter | None = channel.get_chatter(requester.name)

                if chatter and isinstance(chatter, twitchio.Chatter):
                    badge_html = self.get_badge_html(chatter)

            elif not requester:
                badge_html = (
                    """<img src="https://static-cdn.jtvnw.net/badges/v1/3267646d-33f0-4b17-b3df-f923a41db1d0/2" />"""
                )

            html = f"""
            <div class="queueTrack">
                <div class="queueTrackMeta">
                    <img src="{artwork}" alt="Album Artwork">
                    <a class="queueTrackMetaTitle" href="{track.uri}" target="_blank">
                        <span style="filter: brightness(90%);">{title}</span>
                        <small style="filter: brightness(60%);">{author}</small>
                        <small style="filter: brightness(40%);">{player.ms_to_hr(duration)}</small>
                    </a>
                </div>

                <div class="queueTrackRequester hover">
                    <div class="tooltip requesterTooltip">
                        <img src="{requester_img}" alt="Requester Image">
                        <a href="{requester_url}">{requested}</a>
                        <div class="requesterBadges">
                            {badge_html}
                        </div>
                    </div>
                    <img src="{requester_img}" alt="Requester Image">
                </div>
            </div>
            """
            track_html.append(html)

        return HTMLResponse("\n".join(track_html))

    @route("/history", methods=["GET"])
    @limit(core.config["LIMITS"]["player_queues"]["rate"], core.config["LIMITS"]["player_queues"]["per"])
    async def get_player_history(self, request: Request) -> Response:
        session: dict[str, Any] = request.session
        if not session:
            return HTMLResponse("""<a href="/playerdashboard/login">Login</a>""")

        player: core.Player | None
        player = wavelink.Pool.get_node().get_player(core.TIME_GUILD)  # type: ignore

        if not player or not hasattr(player, "loaded"):
            html = """<b>No history available.</b>"""
            return HTMLResponse(html)

        track_html: list[str] = []

        queues = list(player.queue.history) + list(player.auto_queue.history)  # type: ignore
        for track in reversed(queues):  # type: ignore
            artwork = track.artwork or "/static/img/album_placeholder.png"
            title = f"{escape(track.title)[:40]}{'...' if len(track.title) > 40 else ''}"
            author = f"{escape(track.author)[:40]}{'...' if len(track.author) > 40 else ''}"
            duration = track.length

            requester: twitchio.User | None = getattr(track, "twitch_user", None)
            requested: str = f"{requester.display_name}" if requester else "Bot AutoPlay"
            requester_url: str = f"https://twitch.tv/{requester.name}" if requester else "https://twitch.tv/thetimebot"
            requester_img: str = requester.profile_image if requester else "/static/img/time_bot.png"

            badge_html: str = ""
            channel: twitchio.Channel | None = self.app.tbot.get_channel("timeenjoyed")
            if requester and channel:
                chatter: twitchio.Chatter | twitchio.PartialChatter | None = channel.get_chatter(requester.name)

                if chatter and isinstance(chatter, twitchio.Chatter):
                    badge_html = self.get_badge_html(chatter)

            elif not requester:
                badge_html = (
                    """<img src="https://static-cdn.jtvnw.net/badges/v1/3267646d-33f0-4b17-b3df-f923a41db1d0/2" />"""
                )

            uid: int | None = session.get("id")
            if uid:
                if uid not in self.liked:
                    self.liked[uid] = []

                if track.identifier in self.liked[uid]:
                    fave: str = """<span class="material-symbols-rounded liked">favorite</span>"""
                else:
                    fave = f"""<span class="material-symbols-rounded notLiked" hx-post="/playerdashboard/like?identifier={urllib.parse.quote(track.identifier)}&uri={urllib.parse.quote(str(track.uri))}" hx-swap="outerHTML">favorite</span>"""

            html = f"""
            <div class="queueTrack">
                <div class="queueTrackMeta">
                    <img src="{artwork}" alt="Album Artwork">
                    <a class="queueTrackMetaTitle" href="{track.uri}" target="_blank">
                        <span style="filter: brightness(90%);">{title}</span>
                        <small style="filter: brightness(60%);">{author}</small>
                        <small style="filter: brightness(40%);">{player.ms_to_hr(duration)}</small>
                    </a>
                </div>

                <div class="historyEnd">
                    {fave}

                    <div class="queueTrackRequester hover">
                        <div class="tooltip requesterTooltip">
                            <img src="{requester_img}" alt="Requester Image">
                            <a href="{requester_url}">{requested}</a>
                            <div class="requesterBadges">
                                {badge_html}
                            </div>
                        </div>
                        <img src="{requester_img}" alt="Requester Image">
                    </div>
                </div>
            </div>
            """
            track_html.append(html)

        return HTMLResponse("\n".join(track_html))

    @route("/requests", methods=["GET"])
    @limit(core.config["LIMITS"]["player_queues"]["rate"], core.config["LIMITS"]["player_queues"]["per"])
    async def get_player_requests(self, request: Request) -> Response:
        session: dict[str, Any] = request.session
        if not session:
            return HTMLResponse("""<a href="/playerdashboard/login">Login</a>""")

        player: core.Player | None
        player = wavelink.Pool.get_node().get_player(core.TIME_GUILD)  # type: ignore

        if not player or not hasattr(player, "loaded"):
            html = """<b>No player is currently active.</b>"""
            return HTMLResponse(html)

        html = """
        <span>Requests</span>
        """
        return HTMLResponse(html)

    @route("/user", methods=["GET"])
    async def get_user(self, request: Request) -> Response:
        session: dict[str, Any] = request.session
        if not session:
            return HTMLResponse("""<a href="/playerdashboard/login">Login</a>""")

        html = """
            <div class="user">
                <img class="userAvatar" src="{0}" alt="User Avatar">
                <div class="userName">
                {1}
                <small><a href="/playerdashboard/logout"> (Logout)</a></small>
                </div>
            </div>
        """

        avatar: str | None = request.session.get("avatar", None)
        name: str | None = request.session.get("name", None)
        uid: int | None = session.get("id")

        if avatar and name:
            html = html.format(avatar, name)

        elif uid and session.get("service") == "discord":
            discord_user: discord.User | None = await self.app.dbot.fetch_user(uid)

            if discord_user:
                html = html.format(discord_user.display_avatar.url, discord_user.display_name)

        return HTMLResponse(html)

    @route("/footer/playing", methods=["GET"])
    @limit(core.config["LIMITS"]["player_meta"]["rate"], core.config["LIMITS"]["player_meta"]["per"])
    async def get_playing_footer(self, request: Request) -> Response:
        session: dict[str, Any] = request.session
        if not session:
            return HTMLResponse("""<a href="/playerdashboard/login">Login</a>""")

        player: core.Player | None
        player = wavelink.Pool.get_node().get_player(core.TIME_GUILD)  # type: ignore

        if not player or not hasattr(player, "loaded"):
            html = """<b>No player is currently active.</b>"""
            return HTMLResponse(html)

        current: wavelink.Playable | None = player.current
        if not current:
            html = """<b>No track is currently playing.</b>"""
            return HTMLResponse(html)

        title = f"{escape(current.title)[:40]}{'...' if len(current.title) > 40 else ''}"
        author = f"{escape(current.author)[:40]}{'...' if len(current.author) > 40 else ''}"

        fave: str = """<span></span>"""
        uid: int | None = session.get("id")

        if uid and session.get("service") == "discord":
            if uid not in self.liked:
                self.liked[uid] = []

            if current.identifier in self.liked[uid]:
                fave = """<span class="material-symbols-rounded liked">favorite</span>"""
            else:
                fave = f"""<span class="material-symbols-rounded notLiked" hx-post="/playerdashboard/like?identifier={urllib.parse.quote(current.identifier)}&uri={urllib.parse.quote(str(current.uri))}" hx-swap="outerHTML">favorite</span>"""

        send_to: str = """<span></span>"""
        if session.get("moderator", False):
            if current.identifier in self.sent:
                send_to = """<span class="material-symbols-rounded sent">send</span>"""
            else:
                send_to = f"""<span class="material-symbols-rounded notSent" hx-post="/playerdashboard/send?identifier={urllib.parse.quote(current.identifier)}&uri={urllib.parse.quote(str(current.uri))}" hx-swap="innerHTML">send</span>"""

        html = f"""
            <div class="footerTrackMeta">
                <img src="{current.artwork}" alt="Album Artwork">
                <a class="queueTrackMetaTitle" href="{current.uri}" target="_blank">
                    <span style="filter: brightness(90%);">{title}</span>
                    <small style="filter: brightness(60%);">{author}</small>
                    <small style="filter: brightness(40%);">{player.ms_to_hr(current.length)}</small>
                </a>
                {fave}
                {send_to}
            </div>
        """

        return HTMLResponse(html)

    @route("/like", methods=["POST"])
    @limit(core.config["LIMITS"]["player_likes"]["rate"], core.config["LIMITS"]["player_likes"]["per"])
    async def like_track(self, request: Request) -> Response:
        player: core.Player | None
        player = wavelink.Pool.get_node().get_player(core.TIME_GUILD)  # type: ignore

        if not player or not hasattr(player, "loaded"):
            return Response("No player is currently active.", status_code=400)

        session: dict[str, Any] = request.session
        if not session:
            return Response("Unauthorized", status_code=401)

        uid: int | None = session.get("id")
        if not uid or request.session.get("service") != "discord":
            return Response("Unauthorized", status_code=401)

        identifier: str = urllib.parse.unquote(request.query_params.get("identifier", ""))
        uri: str = urllib.parse.unquote(request.query_params.get("uri", ""))

        if not identifier or not uri:
            return Response("Invalid Request", status_code=400)

        guild: discord.Guild | None = self.app.dbot.get_guild(core.TIME_GUILD)
        if not guild:
            return Response("Internal Server Error", status_code=500)

        member: discord.Member | None = guild.get_member(uid)
        if not member:
            return Response("Unauthorized", status_code=401)

        if member.id not in self.liked:
            self.liked[member.id] = []

        if identifier in self.liked[member.id]:
            return HTMLResponse("<span class='material-symbols-rounded liked'>favorite</span>")

        if player.thread:
            try:
                await player.thread.send(f"Hey {member.mention}, you liked this song from stream:\n{uri}")
            except discord.HTTPException:
                return Response("Internal Server Error", status_code=500)

        self.liked[member.id].append(identifier)

        headers: dict[str, str] = {"HX-Trigger": "likedSong"}
        return HTMLResponse("<span class='material-symbols-rounded liked'>favorite</span>", headers=headers)

    @route("/send", methods=["POST"])
    @limit(core.config["LIMITS"]["player_likes"]["rate"], core.config["LIMITS"]["player_likes"]["per"])
    async def send_track(self, request: Request) -> Response:
        identifier: str = urllib.parse.unquote(request.query_params.get("identifier", ""))
        uri: str = urllib.parse.unquote(request.query_params.get("uri", ""))

        if identifier in self.sent:
            return HTMLResponse("""<span class="material-symbols-rounded sent">send</span>""")

        session: dict[str, Any] = request.session
        if not session:
            return Response("Unauthorized", status_code=401)

        uid: int | None = session.get("id")
        if not uid or request.session.get("service") != "discord":
            return Response("Unauthorized", status_code=401)

        if not identifier or not uri:
            return Response("Invalid Request", status_code=400)

        guild: discord.Guild | None = self.app.dbot.get_guild(core.TIME_GUILD)
        if not guild:
            return Response("Internal Server Error", status_code=500)

        member: discord.Member | None = guild.get_member(uid)
        if not member:
            return Response("Unauthorized", status_code=401)

        if not member.guild_permissions.kick_members:
            return Response("Unauthorized", status_code=401)

        message: str = f"**Sent via Dashboard:**\n{uri}"
        async with aiohttp.ClientSession() as session_:
            url: str = core.config["GENERAL"]["music_webhook"]
            webhook: discord.Webhook = discord.Webhook.from_url(url=url, session=session_)

            await webhook.send(content=message, avatar_url=member.display_avatar.url, username=member.display_name)

        self.sent.append(identifier)
        await self.app.dispatch_htmx("sent_song", data={"data": ""})

        return HTMLResponse("""<span class="material-symbols-rounded sent">send</span>""")
