from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .calendar_es import SpainNationalHolidaysCalendar, working_seconds
from .config import (
    DT_FORMAT,
    SLA_ENTITY_TYPES,
    OLA_ENTITY_TYPES,
    SLA_STOP_TYPES,
    OLA_STOP_TYPES,
)
from .intervals import Interval, merge_intervals
from .models import CalcResult, EntityInput


def _dt_str(dt) -> str:
    return dt.strftime(DT_FORMAT)


def calculate(entity: EntityInput) -> CalcResult:
    """
    Deterministic oracle:
    - Model A working time: 24h Mon-Fri excluding ES holidays + weekends
    - Stops: clip to lifecycle window + merge overlaps
    - SLA entities: Global stops
    - OLA entities: Global+Interna+Externa stops
    - If not finalized: compute TTD and to-date KPIs; real KPIs are None
    """
    cal = SpainNationalHolidaysCalendar()

    window_start = entity.start
    real_end = entity.end if entity.is_finalized and entity.end is not None else None
    to_date_end = entity.now

    # Base durations
    ttd = working_seconds(entity.start, entity.now, cal)
    ttm = working_seconds(entity.start, entity.end, cal) if real_end else None

    def clip_merge_for(stop_types: set[str], w_end) -> Tuple[List[Interval], List[Dict[str, Any]]]:
        raw: List[Interval] = []
        evidence: List[Dict[str, Any]] = []

        for s in entity.stops:
            if s.stop_type not in stop_types:
                continue

            iv = Interval(s.start, s.end)
            if not iv.is_valid():
                evidence.append({
                    "stop_type": s.stop_type,
                    "original": {"start": _dt_str(s.start), "end": _dt_str(s.end)},
                    "action": "rejected_invalid_interval",
                })
                continue

            clipped = iv.clip(window_start, w_end)
            if clipped is None:
                evidence.append({
                    "stop_type": s.stop_type,
                    "original": {"start": _dt_str(s.start), "end": _dt_str(s.end)},
                    "action": "discarded_outside_window",
                })
                continue

            action = "kept" if (clipped.start == iv.start and clipped.end == iv.end) else "clipped_to_window"
            evidence.append({
                "stop_type": s.stop_type,
                "original": {"start": _dt_str(s.start), "end": _dt_str(s.end)},
                "clipped": {"start": _dt_str(clipped.start), "end": _dt_str(clipped.end)},
                "action": action,
            })
            raw.append(clipped)

        merged = merge_intervals(raw)
        return merged, evidence

    def sum_working(intervals: List[Interval]) -> int:
        return sum(working_seconds(iv.start, iv.end, cal) for iv in intervals)

    # Stops (Real) only if finalized
    merged_sla_real: List[Interval] = []
    merged_ola_real: List[Interval] = []
    evidence_sla_real: List[Dict[str, Any]] = []
    evidence_ola_real: List[Dict[str, Any]] = []

    if real_end:
        merged_sla_real, evidence_sla_real = clip_merge_for(SLA_STOP_TYPES, real_end)
        merged_ola_real, evidence_ola_real = clip_merge_for(OLA_STOP_TYPES, real_end)

    stops_sla_real = sum_working(merged_sla_real) if real_end else 0
    stops_ola_real = sum_working(merged_ola_real) if real_end else 0

    # Stops (To date) always
    merged_sla_td, evidence_sla_td = clip_merge_for(SLA_STOP_TYPES, to_date_end)
    merged_ola_td, evidence_ola_td = clip_merge_for(OLA_STOP_TYPES, to_date_end)

    stops_sla_td = sum_working(merged_sla_td)
    stops_ola_td = sum_working(merged_ola_td)

    is_sla_entity = entity.entity_type in SLA_ENTITY_TYPES
    is_ola_entity = entity.entity_type in OLA_ENTITY_TYPES

    sla_real = None
    ola_real = None
    if real_end and ttm is not None:
        if is_sla_entity:
            sla_real = max(0, ttm - stops_sla_real)
        if is_ola_entity:
            ola_real = max(0, ttm - stops_ola_real)

    sla_to_date = max(0, ttd - stops_sla_td) if is_sla_entity else None
    ola_to_date = max(0, ttd - stops_ola_td) if is_ola_entity else None

    explain: Dict[str, Any] = {
        "calendar": {
            "mode": "Model A (24h Mon-Fri) excluding weekends + ES national holidays",
        },
        "entity": {
            "entity_type": entity.entity_type,
            "is_finalized": entity.is_finalized,
            "start": _dt_str(entity.start),
            "end": _dt_str(entity.end) if entity.end else None,
            "now": _dt_str(entity.now),
        },
        "windows": {
            "real_window": {"start": _dt_str(entity.start), "end": _dt_str(entity.end) if entity.end else None},
            "to_date_window": {"start": _dt_str(entity.start), "end": _dt_str(entity.now)},
        },
        "stops": {
            "sla_real": {
                "evidence": evidence_sla_real,
                "merged_intervals": [{"start": _dt_str(i.start), "end": _dt_str(i.end)} for i in merged_sla_real],
                "working_seconds": stops_sla_real,
            },
            "ola_real": {
                "evidence": evidence_ola_real,
                "merged_intervals": [{"start": _dt_str(i.start), "end": _dt_str(i.end)} for i in merged_ola_real],
                "working_seconds": stops_ola_real,
            },
            "sla_to_date": {
                "evidence": evidence_sla_td,
                "merged_intervals": [{"start": _dt_str(i.start), "end": _dt_str(i.end)} for i in merged_sla_td],
                "working_seconds": stops_sla_td,
            },
            "ola_to_date": {
                "evidence": evidence_ola_td,
                "merged_intervals": [{"start": _dt_str(i.start), "end": _dt_str(i.end)} for i in merged_ola_td],
                "working_seconds": stops_ola_td,
            },
        },
        "durations": {
            "ttd_working_seconds": ttd,
            "ttm_working_seconds": ttm,
        },
    }

    # Para facilitar QA: devolvemos "stops_*_seconds" según estado
    stops_sla_effective = stops_sla_real if real_end else stops_sla_td
    stops_ola_effective = stops_ola_real if real_end else stops_ola_td

    return CalcResult(
        ttd_seconds=ttd,
        ttm_seconds=ttm,
        stops_sla_seconds=stops_sla_effective,
        stops_ola_seconds=stops_ola_effective,
        sla_real_seconds=sla_real,
        sla_to_date_seconds=sla_to_date,
        ola_real_seconds=ola_real,
        ola_to_date_seconds=ola_to_date,
        explain=explain,
    )