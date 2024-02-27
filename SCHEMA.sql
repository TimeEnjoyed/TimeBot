-- Active: 1703653682760@@127.0.0.1@5432@timebot_test
CREATE TABLE IF NOT EXISTS users (
    uid BIGINT PRIMARY KEY,
    discord_id BIGINT UNIQUE,
    twitch_id BIGINT UNIQUE,
    moderator BOOLEAN NOT NULL DEFAULT false,
    token TEXT UNIQUE NOT NULL,
    created TIMESTAMP DEFAULT (now() at time zone 'utc'),
    points BIGINT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS state (
    code TEXT PRIMARY KEY,
    discord_id BIGINT UNIQUE NOT NULL,
    moderator BOOLEAN DEFAULT false
);

CREATE TABLE IF NOT EXISTS quotes (
    id SERIAL PRIMARY KEY,
    content TEXT UNIQUE NOT NULL,
    added_by BIGINT NOT NULL,
    speaker BIGINT,
    source TEXT NOT NULL,
    created TIMESTAMP DEFAULT (now() at time zone 'utc')
);