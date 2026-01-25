from __future__ import annotations

import json
from typing import List

from .models import EntityInput, Stop
from .parsing import parse_dt


def load_entity_input(path: str) -> EntityInput:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    entity_type = data["entity_type"]
    is_finalized = bool(data["is_finalized"])
    start = parse_dt(data["start"])
    now = parse_dt(data["now"])
    end = parse_dt(data["end"]) if data.get("end") else None

    stops: List[Stop] = []
    for s in data.get("stops", []):
        stops.append(
            Stop(
                stop_type=s["type"],
                start=parse_dt(s["start"]),
                end=parse_dt(s["end"]),
            )
        )

    return EntityInput(
        entity_type=entity_type,
        start=start,
        end=end,
        is_finalized=is_finalized,
        now=now,
        stops=stops,
    )