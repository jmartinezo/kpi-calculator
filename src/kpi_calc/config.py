from __future__ import annotations

# Formato de entrada/salida de fechas (inputs cliente)
DT_FORMAT = "%d/%m/%Y - %H:%M"

# Tipos de entidades por familia de KPI
SLA_ENTITY_TYPES = {
    "Viabilidades", "Viabilidad",
    "Subviabilidades", "Subviabilidad",
    "Provisión", "Provision",
    "Provisión/Proyecto", "Provision/Proyecto",
    "PIP",
}

OLA_ENTITY_TYPES = {
    "Servicio interno",
    "Tarea",
}

# Tipos de parada aplicables por familia
SLA_STOP_TYPES = {"Global"}
OLA_STOP_TYPES = {"Global", "Interna", "Externa"}