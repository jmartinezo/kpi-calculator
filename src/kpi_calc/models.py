from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional


StopType = Literal["Global", "Interna", "Externa"]


@dataclass
class Stop:
    stop_type: StopType
    start: datetime
    end: datetime


@dataclass
class EntityInput:
    entity_type: str
    start: datetime
    end: Optional[datetime]          # solo si finalizada
    is_finalized: bool
    now: datetime                   # current date del cliente (reproducible)
    stops: List[Stop]


@dataclass
class CalcResult:
    # Base durations
    ttd_seconds: int
    ttm_seconds: Optional[int]

    # Stop totals (por ventana aplicable: real o to-date)
    stops_sla_seconds: int
    stops_ola_seconds: int

    # KPI outputs (seconds)
    sla_real_seconds: Optional[int]
    sla_to_date_seconds: Optional[int]
    ola_real_seconds: Optional[int]
    ola_to_date_seconds: Optional[int]

    # Explain / evidence
    explain: Dict[str, Any]