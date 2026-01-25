from __future__ import annotations

from datetime import datetime
from .config import DT_FORMAT


def parse_dt(s: str) -> datetime:
    """
    Parse datetime in format 'dd/mm/yyyy - HH:MM' (Europe/Madrid local time, naive).
    We keep naive datetimes because inputs are client-side and DST is out of scope for now.
    """
    return datetime.strptime(s, DT_FORMAT)