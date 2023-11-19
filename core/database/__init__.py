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


__all__ = ("Database", )


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
