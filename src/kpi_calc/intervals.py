from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass(frozen=True)
class Interval:
    start: datetime
    end: datetime

    def is_valid(self) -> bool:
        return self.end > self.start

    def clip(self, window_start: datetime, window_end: datetime) -> Optional["Interval"]:
        """
        Clip interval to [window_start, window_end]. If no overlap, return None.
        """
        if self.end <= window_start or self.start >= window_end:
            return None
        new_start = max(self.start, window_start)
        new_end = min(self.end, window_end)
        clipped = Interval(new_start, new_end)
        return clipped if clipped.is_valid() else None


def merge_intervals(intervals: List[Interval]) -> List[Interval]:
    """
    Merge overlapping/touching intervals. Touching means end == next.start.
    """
    valid = [i for i in intervals if i.is_valid()]
    if not valid:
        return []

    valid.sort(key=lambda x: x.start)
    merged: List[Interval] = [valid[0]]

    for cur in valid[1:]:
        last = merged[-1]
        if cur.start <= last.end:
            merged[-1] = Interval(last.start, max(last.end, cur.end))
        else:
            merged.append(cur)

    return merged