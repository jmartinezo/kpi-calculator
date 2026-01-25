from __future__ import annotations

import argparse
import json

from .calculator import calculate
from .config import SLA_ENTITY_TYPES, OLA_ENTITY_TYPES
from .formatting import fmt_duration_dhm
from .io_json import load_entity_input


def main() -> None:
    ap = argparse.ArgumentParser(
        description="KPI calculator (SLA/OLA) with stops; excludes weekends + ES national holidays (Model A 24h Mon-Fri)."
    )
    ap.add_argument("--input", required=True, help="Path to input JSON.")
    ap.add_argument("--explain", action="store_true", help="Print explain/evidence JSON.")
    args = ap.parse_args()

    entity = load_entity_input(args.input)
    res = calculate(entity)

    print("=== KPI Calculator Results ===")
    print(f"Entity type: {entity.entity_type}")
    print(f"Finalized: {entity.is_finalized}")
    print(f"TTD (working): {fmt_duration_dhm(res.ttd_seconds)}")

    if entity.is_finalized and res.ttm_seconds is not None:
        print(f"TTM (working): {fmt_duration_dhm(res.ttm_seconds)}")

    if entity.entity_type in SLA_ENTITY_TYPES:
        if entity.is_finalized and res.sla_real_seconds is not None:
            print(f"SLA Real: {fmt_duration_dhm(res.sla_real_seconds)}")
        if res.sla_to_date_seconds is not None:
            print(f"SLA a fecha actual: {fmt_duration_dhm(res.sla_to_date_seconds)}")

    if entity.entity_type in OLA_ENTITY_TYPES:
        if entity.is_finalized and res.ola_real_seconds is not None:
            print(f"OLA Real: {fmt_duration_dhm(res.ola_real_seconds)}")
        if res.ola_to_date_seconds is not None:
            print(f"OLA a fecha actual: {fmt_duration_dhm(res.ola_to_date_seconds)}")

    if args.explain:
        print("\n=== Explain / Evidence ===")
        print(json.dumps(res.explain, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()