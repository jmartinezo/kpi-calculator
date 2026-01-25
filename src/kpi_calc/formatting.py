from __future__ import annotations

import math


def ceil_seconds_to_minutes(seconds: int) -> int:
    """Ceil seconds to the next minute boundary (keeping seconds as int)."""
    if seconds <= 0:
        return 0
    return int(math.ceil(seconds / 60.0) * 60)


def fmt_duration_dhm(seconds: int) -> str:
    """
    Format as 'DD d HH h MM m', rounding UP seconds to minutes as requested.
    """
    seconds = ceil_seconds_to_minutes(int(seconds))
    minutes = seconds // 60

    days = minutes // (24 * 60)
    minutes -= days * 24 * 60

    hours = minutes // 60
    minutes -= hours * 60

    return f"{days:02d} d {hours:02d} h {minutes:02d} m"