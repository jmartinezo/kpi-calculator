from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from kpi_calc.calculator import calculate
from kpi_calc.config import SLA_ENTITY_TYPES, OLA_ENTITY_TYPES, DT_FORMAT
from kpi_calc.formatting import fmt_duration_dhm
from kpi_calc.models import EntityInput, Stop
from kpi_calc.parsing import parse_dt


# ----------------------------
# Helpers UI
# ----------------------------

ENTITY_TYPES = [
    "Viabilidad",
    "Subviabilidad",
    "Provisión",
    "Provisión/Proyecto",
    "PIP",
    "Servicio interno",
    "Tarea",
]

STOP_TYPES = ["Global", "Interna", "Externa"]


def dt_to_str(dt: datetime) -> str:
    return dt.strftime(DT_FORMAT)


def str_to_dt(s: str) -> datetime:
    return parse_dt(s)


def default_now_str() -> str:
    return dt_to_str(datetime.now())


def init_session_state() -> None:
    if "entity_type" not in st.session_state:
        st.session_state.entity_type = "Viabilidad"

    if "is_finalized" not in st.session_state:
        st.session_state.is_finalized = False

    if "start_str" not in st.session_state:
        st.session_state.start_str = dt_to_str(datetime.now().replace(hour=9, minute=0, second=0, microsecond=0))

    if "end_str" not in st.session_state:
        st.session_state.end_str = dt_to_str(datetime.now().replace(hour=18, minute=0, second=0, microsecond=0))

    if "now_str" not in st.session_state:
        st.session_state.now_str = default_now_str()

    if "stops_df" not in st.session_state:
        st.session_state.stops_df = pd.DataFrame(
            [
                {"Tipo": "Global", "Inicio": dt_to_str(datetime.now()), "Fin": dt_to_str(datetime.now())}
            ]
        )


def build_entity_input() -> EntityInput:
    entity_type = st.session_state.entity_type
    is_finalized = st.session_state.is_finalized

    start = str_to_dt(st.session_state.start_str)
    now = str_to_dt(st.session_state.now_str)

    end: Optional[datetime] = None
    if is_finalized:
        end = str_to_dt(st.session_state.end_str)

    stops: List[Stop] = []
    df = st.session_state.stops_df.copy()

    # Normaliza NaNs y tipos
    for _, row in df.iterrows():
        stop_type = str(row.get("Tipo", "")).strip()
        start_s = str(row.get("Inicio", "")).strip()
        end_s = str(row.get("Fin", "")).strip()

        if not stop_type or not start_s or not end_s:
            continue

        stops.append(
            Stop(
                stop_type=stop_type,  # type: ignore
                start=str_to_dt(start_s),
                end=str_to_dt(end_s),
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


def validate_inputs(entity: EntityInput) -> List[str]:
    errors: List[str] = []

    if entity.now <= entity.start:
        errors.append("La fecha actual (now) debe ser posterior a la fecha de inicio.")

    if entity.is_finalized:
        if entity.end is None:
            errors.append("La entidad está marcada como finalizada pero la fecha fin está vacía.")
        elif entity.end <= entity.start:
            errors.append("La fecha fin debe ser posterior a la fecha de inicio.")

    for idx, s in enumerate(entity.stops, start=1):
        if s.end <= s.start:
            errors.append(f"Parada #{idx}: la fecha fin debe ser posterior a la fecha inicio.")
        if s.stop_type not in STOP_TYPES:
            errors.append(f"Parada #{idx}: tipo de parada inválido ({s.stop_type}).")

    # Validación de coherencia familia KPI
    if entity.entity_type not in ENTITY_TYPES:
        errors.append("Tipo de entidad no reconocido.")

    return errors


def build_case_json(entity: EntityInput) -> Dict[str, Any]:
    return {
        "entity_type": entity.entity_type,
        "is_finalized": entity.is_finalized,
        "start": dt_to_str(entity.start),
        "end": dt_to_str(entity.end) if entity.end else None,
        "now": dt_to_str(entity.now),
        "stops": [
            {"type": s.stop_type, "start": dt_to_str(s.start), "end": dt_to_str(s.end)} for s in entity.stops
        ],
    }


# ----------------------------
# App
# ----------------------------

def main() -> None:
    st.set_page_config(page_title="Calculadora KPI (SLA/OLA)", layout="wide")
    init_session_state()

    st.title("Calculadora KPI (SLA/OLA) — Herramienta de Pruebas")

    st.caption(
        "Modelo A: tiempo hábil = 24h de lunes a viernes, excluyendo sábados, domingos y festivos nacionales comunes (España). "
        "Las paradas se recortan al ciclo de vida, se fusionan si solapan y se descuentan en tiempo hábil."
    )

    col_left, col_right = st.columns([1.1, 1.4], gap="large")

    # -------- Left: Inputs
    with col_left:
        st.subheader("1) Datos de la entidad")

        st.selectbox("Tipo de entidad", ENTITY_TYPES, key="entity_type")
        st.checkbox("Entidad finalizada", key="is_finalized")

        st.text_input(f"Fecha inicio ({DT_FORMAT})", key="start_str")
        if st.session_state.is_finalized:
            st.text_input(f"Fecha fin ({DT_FORMAT})", key="end_str")
        st.text_input(f"Fecha actual (now) ({DT_FORMAT})", key="now_str")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Now = ahora"):
                st.session_state.now_str = default_now_str()
        with c2:
            if st.button("Limpiar paradas"):
                st.session_state.stops_df = pd.DataFrame(columns=["Tipo", "Inicio", "Fin"])

        st.subheader("2) Paradas")
        st.caption("Edita la tabla. Formato de fecha: dd/mm/yyyy - HH:MM")

        # Editor de tabla (Streamlit >= 1.19)
        st.session_state.stops_df = st.data_editor(
            st.session_state.stops_df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Tipo": st.column_config.SelectboxColumn("Tipo", options=STOP_TYPES, required=True),
                "Inicio": st.column_config.TextColumn("Inicio", required=True),
                "Fin": st.column_config.TextColumn("Fin", required=True),
            },
        )

        st.divider()
        uploaded = st.file_uploader("Cargar caso (JSON)", type=["json"])
        if uploaded is not None:
            try:
                data = json.loads(uploaded.read().decode("utf-8"))
                st.session_state.entity_type = data["entity_type"]
                st.session_state.is_finalized = bool(data["is_finalized"])
                st.session_state.start_str = data["start"]
                st.session_state.end_str = data.get("end") or st.session_state.end_str
                st.session_state.now_str = data["now"]

                stops = data.get("stops", [])
                st.session_state.stops_df = pd.DataFrame(
                    [{"Tipo": s["type"], "Inicio": s["start"], "Fin": s["end"]} for s in stops]
                )
                st.success("Caso cargado correctamente.")
            except Exception as e:
                st.error(f"No se pudo cargar el caso: {e}")

    # -------- Right: Results
    with col_right:
        st.subheader("3) Resultados")

        btn_calc = st.button("Calcular KPIs", type="primary", use_container_width=True)

        if btn_calc:
            try:
                entity = build_entity_input()
                errors = validate_inputs(entity)
                if errors:
                    for err in errors:
                        st.error(err)
                else:
                    res = calculate(entity)

                    # KPIs aplicables por tipo de entidad
                    is_sla_entity = entity.entity_type in SLA_ENTITY_TYPES
                    is_ola_entity = entity.entity_type in OLA_ENTITY_TYPES

                    kpi_cols = st.columns(3)
                    kpi_cols[0].metric("TTD (hábil)", fmt_duration_dhm(res.ttd_seconds))
                    if entity.is_finalized and res.ttm_seconds is not None:
                        kpi_cols[1].metric("TTM (hábil)", fmt_duration_dhm(res.ttm_seconds))
                    else:
                        kpi_cols[1].metric("TTM (hábil)", "—")

                    # Stops totals (effective)
                    # (para QA: lo mostramos claro)
                    if is_sla_entity:
                        kpi_cols[2].metric("Paradas SLA (hábil)", fmt_duration_dhm(res.stops_sla_seconds))
                    elif is_ola_entity:
                        kpi_cols[2].metric("Paradas OLA (hábil)", fmt_duration_dhm(res.stops_ola_seconds))
                    else:
                        kpi_cols[2].metric("Paradas (hábil)", "—")

                    st.divider()

                    out_cols = st.columns(2)
                    with out_cols[0]:
                        st.markdown("**KPIs SLA**")
                        if is_sla_entity:
                            if entity.is_finalized and res.sla_real_seconds is not None:
                                st.write(f"- SLA Real: **{fmt_duration_dhm(res.sla_real_seconds)}**")
                            st.write(f"- SLA a fecha actual: **{fmt_duration_dhm(res.sla_to_date_seconds or 0)}**")
                        else:
                            st.write("No aplica para este tipo de entidad.")

                    with out_cols[1]:
                        st.markdown("**KPIs OLA**")
                        if is_ola_entity:
                            if entity.is_finalized and res.ola_real_seconds is not None:
                                st.write(f"- OLA Real: **{fmt_duration_dhm(res.ola_real_seconds)}**")
                            st.write(f"- OLA a fecha actual: **{fmt_duration_dhm(res.ola_to_date_seconds or 0)}**")
                        else:
                            st.write("No aplica para este tipo de entidad.")

                    st.divider()

                    # Evidence / Explain
                    with st.expander("Evidencia (intervalos fusionados y decisiones)"):
                        st.json(res.explain)

                    # Export buttons
                    entity_case = build_case_json(entity)
                    evidence = {
                        "case": entity_case,
                        "result": {
                            "ttd": fmt_duration_dhm(res.ttd_seconds),
                            "ttm": fmt_duration_dhm(res.ttm_seconds) if res.ttm_seconds is not None else None,
                            "sla_real": fmt_duration_dhm(res.sla_real_seconds) if res.sla_real_seconds is not None else None,
                            "sla_to_date": fmt_duration_dhm(res.sla_to_date_seconds) if res.sla_to_date_seconds is not None else None,
                            "ola_real": fmt_duration_dhm(res.ola_real_seconds) if res.ola_real_seconds is not None else None,
                            "ola_to_date": fmt_duration_dhm(res.ola_to_date_seconds) if res.ola_to_date_seconds is not None else None,
                        },
                        "explain": res.explain,
                    }

                    b1, b2 = st.columns(2)
                    with b1:
                        st.download_button(
                            "Exportar caso (JSON)",
                            data=json.dumps(entity_case, ensure_ascii=False, indent=2),
                            file_name="case.json",
                            mime="application/json",
                            use_container_width=True,
                        )
                    with b2:
                        st.download_button(
                            "Exportar evidencia (JSON)",
                            data=json.dumps(evidence, ensure_ascii=False, indent=2),
                            file_name="evidence.json",
                            mime="application/json",
                            use_container_width=True,
                        )

            except Exception as e:
                st.error(f"Error durante el cálculo: {e}")


if __name__ == "__main__":
    main()