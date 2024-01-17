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
import datetime


__all__ = ("format_day",)

ORDINALS: dict[int, str] = {1: "st", 2: "nd", 3: "rd", 4: "th"}
SUPERSCRIPT_TABLE = str.maketrans("".join(ORDINALS.values()), "\u02E2\u1D57\u207F\u1D48\u02B3\u1D48\u1D57\u02B0")


def format_day(date: datetime.datetime | int, *, superscript: bool = False) -> str:
    day_int: int = date if isinstance(date, int) else date.day
    ordinal: str = ORDINALS.get(day_int % 10, "th") if day_int not in (11, 12, 13) else "th"

    day: str = f"{day_int}{ordinal}"
    if superscript:
        return day.translate(SUPERSCRIPT_TABLE)

    return day
