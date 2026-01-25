from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, Set

import holidays

@dataclass
class SpainNationalHolidaysCalendar:
    """
    Model A: laborable = 24h (00:00-24:00) de lunes a viernes,
    excluyendo sábados, domingos y festivos nacionales (España).

    Nota: "holidays" devuelve festivos por país. Para "solo nacionales comunes",
    si en el futuro necesitas un filtrado más estricto, añadiremos una capa de filtrado.
    """

    _cache: Dict[int, Set[date]] = None  # lazy

    def __post_init__(self) -> None:
        if self._cache is None:
            self._cache = {}

    def holidays_for_year(self, year: int) -> Set[date]:
        if year in self._cache:
            return self._cache[year]
        es = holidays.country_holidays("ES", years=[year])
        self._cache[year] = set(es.keys())
        return self._cache[year]

    def is_working_day(self, d: date) -> bool:
        # Weekend exclusion (Saturday=5, Sunday=6)
        if d.weekday() >= 5:
            return False
        # Holiday exclusion
        return d not in self.holidays_for_year(d.year)


def working_seconds(start: datetime, end: datetime, cal: SpainNationalHolidaysCalendar) -> int:
    """
    Compute working seconds between [start, end), where working time is
    24h on working days (Mon-Fri) excluding holidays.
    """
    if end <= start:
        return 0

    total = 0
    cursor = start

    # iterate by day; for each day add overlap with [00:00, 24:00) if working day
    while cursor.date() <= end.date():
        day_start = datetime(cursor.year, cursor.month, cursor.day, 0, 0)
        day_end = day_start + timedelta(days=1)

        seg_start = max(start, day_start)
        seg_end = min(end, day_end)

        if seg_end > seg_start and cal.is_working_day(day_start.date()):
            total += int((seg_end - seg_start).total_seconds())

        cursor = day_end

    return total