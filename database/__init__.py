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

    async def fetch_user(self, token: str) -> None:
        ...

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
