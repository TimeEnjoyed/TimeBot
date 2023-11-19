CREATE TABLE IF NOT EXISTS users (
    uid BIGINT PRIMARY KEY,
    discord_id BIGINT,
    twitch_id BIGINT,
    moderator BOOLEAN NOT NULL DEFAULT false,
    token TEXT NOT NULL,
    created TIMESTAMP DEFAULT (now() at time zone 'utc')
);