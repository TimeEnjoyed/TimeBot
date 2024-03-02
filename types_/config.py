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
from typing import TypedDict


class Discord(TypedDict):
    prefix: str
    token: str
    client_id: str
    client_secret: str


class Twitch(TypedDict):
    prefix: str
    token: str
    app_token: str
    channels: list[str]
    client_id: str
    client_secret: str
    eventsub_secret: str
    online_subscriptions: list[str]


class Api(TypedDict):
    prefix: str
    port: int
    public_host: str
    secret: str
    max_age: int


class Database(TypedDict):
    dsn: str


class General(TypedDict):
    stream_refs_id: int
    announcements_id: int
    announcements_webhook: str
    music_webhook: str
    music_channel_id: int
    guild_id: int


class EventSubs(TypedDict):
    events: list[str]
    twitch_id: str
    online_role_id: int
    scopes: list[str]


class Wavelink(TypedDict):
    uri: str
    password: str


class Debug(TypedDict):
    enabled: bool
    access: list[int]


class Redis(TypedDict):
    host: str
    port: int
    db: int


class RateLimit(TypedDict):
    rate: int
    per: int


class Limits(TypedDict):
    sse_player: RateLimit
    quotes: RateLimit
    player_login: RateLimit
    player_oauth: RateLimit
    player_dashboard: RateLimit
    player_queues: RateLimit
    player_meta: RateLimit
    player_likes: RateLimit
    player_json: RateLimit
    twitch_auth: RateLimit


class Config(TypedDict):
    DISCORD: Discord
    TWITCH: Twitch
    API: Api
    DATABASE: Database
    GENERAL: General
    TIME_SUBS: EventSubs
    WAVELINK: Wavelink
    DEBUG: Debug
    REDIS: Redis
    LIMITS: Limits
