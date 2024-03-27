"""Copyright 2023 TimeEnjoyed <https://github.com/TimeEnjoyed/>, 2023 PythonistaGuild <https://github.com/PythonistaGuild>

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

from typing import TYPE_CHECKING

from starlette.authentication import AuthCredentials, AuthenticationBackend, BaseUser


if TYPE_CHECKING:
    from starlette.requests import HTTPConnection

    from api import Server, UserModel


class User(BaseUser):
    def __init__(self, model: UserModel) -> None:
        self.model = model


class AuthBackend(AuthenticationBackend):
    def __init__(self, app: Server) -> None:
        self.app = app

    async def authenticate(self, conn: HTTPConnection) -> tuple[AuthCredentials, User] | None:
        auth: str | None = conn.headers.get("authorization")
        if not auth:
            return

        scopes: list[str] = []
        user: UserModel | None = await self.app.database.fetch_user(token=auth)

        if not user:
            return

        scopes.append("user")
        if user.moderator:
            scopes.append("moderator")

        return AuthCredentials(scopes), User(user)
