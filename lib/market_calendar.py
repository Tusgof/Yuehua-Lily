"""Deterministic NYSE full-session calendar helpers.

Recurring full-day holidays follow the NYSE calendar published at
https://www.nyse.com/markets/hours-calendars.  The two non-recurring closures
inside Lily's sealed 2016-2026 window are 2018-12-05 and 2025-01-09, both
national days of mourning announced by NYSE/ICE.  Early closes remain sessions.
"""

from __future__ import annotations

from datetime import date, timedelta


SPECIAL_FULL_DAY_CLOSURES = {date(2018, 12, 5), date(2025, 1, 9)}


def nyse_sessions(start: date, end: date) -> list[date]:
    if end < start:
        raise ValueError("end must not precede start")
    sessions: list[date] = []
    current = start
    while current <= end:
        if current.weekday() < 5 and current not in _nyse_full_day_closures(current.year):
            sessions.append(current)
        current += timedelta(days=1)
    return sessions


def _nyse_full_day_closures(year: int) -> set[date]:
    closures = {
        _observed(date(year, 1, 1)),
        _nth_weekday(year, 1, 0, 3),
        _nth_weekday(year, 2, 0, 3),
        _easter_sunday(year) - timedelta(days=2),
        _last_weekday(year, 5, 0),
        _observed(date(year, 7, 4)),
        _nth_weekday(year, 9, 0, 1),
        _nth_weekday(year, 11, 3, 4),
        _observed(date(year, 12, 25)),
    }
    if year >= 2022:
        closures.add(_observed(date(year, 6, 19)))
    closures.update(day for day in SPECIAL_FULL_DAY_CLOSURES if day.year == year)
    return closures


def _observed(day: date) -> date:
    if day.weekday() == 5:
        return day - timedelta(days=1)
    if day.weekday() == 6:
        return day + timedelta(days=1)
    return day


def _nth_weekday(year: int, month: int, weekday: int, occurrence: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (occurrence - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    following = date(year + (month == 12), 1 if month == 12 else month + 1, 1)
    last = following - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def _easter_sunday(year: int) -> date:
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day_offset = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day_offset + 1)
