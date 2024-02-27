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

import secrets
from typing import Any, Self

import asyncpg

import core
from api import UserModel, generate_id, generate_token


__all__ = ("Database",)


class Database:
    pool: asyncpg.Pool | None = None

    async def __aenter__(self) -> Self:
        await self.setup()
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self.pool:
            await self.pool.close()

    async def setup(self) -> Self:
        self.pool = await asyncpg.create_pool(dsn=core.config["DATABASE"]["dsn"])
        assert self.pool

        async with self.pool.acquire() as connection:
            with open("SCHEMA.sql") as schema:
                await connection.execute(schema.read())

        return self

    async def create_state(self, *, discord_id: int, moderator: bool = False) -> str:
        assert self.pool

        query: str = """
        INSERT INTO state(code, discord_id, moderator)
        VALUES ($1, $2, $3)
        ON CONFLICT (discord_id) DO UPDATE
        SET code = $1
        """

        code: str = secrets.token_urlsafe(16)
        async with self.pool.acquire() as connection:
            await connection.execute(query, code, discord_id, moderator)

        return code

    async def fetch_user(self, token: str) -> UserModel | None:
        assert self.pool

        query: str = """SELECT * FROM users WHERE token = $1"""
        async with self.pool.acquire() as connection:
            row = await connection.fetchrow(query, token)

        if not row:
            return None

        return UserModel(record=row)

    async def refresh_or_create_user(self, *, twitch_id: int, state: str) -> UserModel:
        assert self.pool

        uid: int = generate_id()
        token: str = generate_token(uid)

        state_query: str = """DELETE FROM state WHERE code = $1 RETURNING *"""
        async with self.pool.acquire() as connection:
            state_row = await connection.fetchrow(state_query, state)

        if not state_row:
            raise ValueError("Improper state was passed. None")

        try:
            discord_id: int = state_row["discord_id"]
            moderator: bool = state_row.get("moderator", False)
        except KeyError:
            raise ValueError("Improper state was passed. Improper data.")

        upsert: str = """
        WITH upsert AS (
            UPDATE users
            SET discord_id = $2, twitch_id = $3, moderator = $4, token = $5
            WHERE discord_id = $2 OR twitch_id = $3
            RETURNING *
        )
        INSERT INTO users(uid, discord_id, twitch_id, moderator, token)
        SELECT $1, $2, $3, $4, $5
        WHERE NOT EXISTS (SELECT * FROM upsert)
        """

        select: str = """
        SELECT * FROM users WHERE token = $1
        """

        async with self.pool.acquire() as connection:
            await connection.execute(upsert, uid, discord_id, twitch_id, moderator, token)
            row = await connection.fetchrow(select, token)

        assert row
        return UserModel(record=row)

    async def create_user(self, *, discord_id: int = 0, twitch_id: int = 0, moderator: bool = False) -> UserModel:
        assert self.pool

        query: str = """
        SELECT * FROM users WHERE discord_id = $1 OR twitch_id = $2
        """
        async with self.pool.acquire() as connection:
            row = await connection.fetchrow(query, discord_id, twitch_id)

            if row:
                return UserModel(record=row)

            uid: int = generate_id()
            token: str = generate_token(uid)

            create_query: str = """
            INSERT INTO users (uid, discord_id, twitch_id, moderator, token) VALUES ($1, $2, $3, $4, $5) RETURNING *
            """
            row = await connection.fetchrow(create_query, uid, discord_id or None, twitch_id or None, moderator, token)

            assert row
            return UserModel(record=row)
    async def upsert_user_twitch(self, *, twitch_id: int, points: int = 0) -> UserModel:
        assert self.pool

        uid: int = generate_id()
        token: str = generate_token(uid)

        # if the user doesn't exist in the db... and you add neg. points, we try to throw
        # if points becomes less than zero
        """
        SET points = users.points
        WHERE points = users.points
        """

        query: str = """
        INSERT INTO users (uid, twitch_id, token, points)
        VALUES ($1, $2, $3, GREATEST($4, 0))
        ON CONFLICT (twitch_id) DO UPDATE
        SET points = GREATEST(users.points + $4, 0)
        RETURNING *
        """

        async with self.pool.acquire() as connection:
            row = await connection.fetchrow(query, uid, twitch_id, token, points)

        assert row
        return UserModel(record=row)

    async def add_quote(
        self, content: str, *, added_by: str | int, source: str, user: str | int | None = None
    ) -> asyncpg.Record:
        assert self.pool

        query: str = """
        INSERT INTO quotes (content, added_by, source, speaker)
        VALUES ($1, $2, $3, $4)
        RETURNING *
        """

        async with self.pool.acquire() as connection:
            if user:
                user = int(user)

            try:
                row: asyncpg.Record = await connection.fetchrow(query, content, int(added_by), source, user)  # type: ignore
            except asyncpg.UniqueViolationError:
                raise ValueError("Quote already exists.")

        assert row
        return row

    async def fetch_quote(self, id_: int, /) -> asyncpg.Record | None:  # / means positional only for teh arg before it
        assert self.pool

        query: str = """
        SELECT * FROM quotes WHERE id = $1
        """

        async with self.pool.acquire() as connection:
            row: asyncpg.Record | None = await connection.fetchrow(query, id_)

        return row

    async def fetch_points(self, twitch_id: int) -> int:
        assert self.pool

        query: str = """
        SELECT points FROM users WHERE twitch_id = $1
        """

        async with self.pool.acquire() as connection:
            row: asyncpg.Record | None = await connection.fetchrow(query, twitch_id)

        assert row
        return row["points"]
