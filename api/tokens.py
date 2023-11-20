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
import base64
import datetime
import secrets


__all__ = ("EPOCH", "generate_id", "generate_token", "id_from_token")


EPOCH: int = 1700394633000  # Sunday, 19 November 2023 11:50:33 AM UTC (Milliseconds)


def generate_id() -> int:
    return int((datetime.datetime.now(tz=datetime.UTC).timestamp() * 1000) - EPOCH)


def generate_token(user_id: int) -> str:
    prefix: str = base64.urlsafe_b64encode(str(user_id).encode(encoding="UTF-8")).decode(encoding="UTF-8")

    secret: str = secrets.token_urlsafe(128)
    token: str = f"TE-{prefix}.{secret}"

    return token


def id_from_token(token: str) -> int | None:
    try:
        encoded: str = token.removeprefix("TE-").split(".")[0]
    except IndexError:
        return None

    try:
        id_: int = int(base64.urlsafe_b64decode(encoded).decode(encoding="UTF-8"))
    except UnicodeDecodeError:
        return None

    return id_
