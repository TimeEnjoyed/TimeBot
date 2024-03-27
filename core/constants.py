from .config import config


__all__ = ("MBTI_TYPES", "TIMEZONES", "TIME_GUILD")


MBTI_TYPES: list[str] = [
    "ESTP",
    "ESTJ",
    "ESFP",
    "ESFJ",
    "ISTP",
    "ISTJ",
    "ISFP",
    "ISFJ",
    "ENFJ",
    "ENTP",
    "ENFP",
    "ENTJ",
    "INTP",
    "INFJ",
    "INTJ",
    "INFP",
]

TIMEZONES: list[str] = [
    "US/Pacific",
    "US/Eastern",
    "Australia/Melbourne",
    "Australia/Brisbane",
    "Africa/Johannesburg",
    "Europe/Helsinki",
    "Europe/London",
    "Japan",
    "Asia/Jakarta",
    "Brazil/East",
    "Asia/Kolkata",
]


TIME_GUILD: int = config["GENERAL"]["guild_id"]
