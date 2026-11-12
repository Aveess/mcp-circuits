"""Runner: orquesta un build completo de punta a punta en el puente.

Secuencia: crear -> construir modelo -> set_code (si hay codigo) ->
reabrir (persistencia) -> inspeccionar -> fidelidad contra la fixture ->
simular y capturar el serial. Cada paso pasa por `probe.run_steps`, asi
que `records` siempre refleja lo que realmente se llamo, en orden.
Solo stdlib + modulos del proyecto.
"""

from __future__ import annotations

import json
import re

from tinkercad_brain.breadboard_nets import derive_nets
from tinkercad_brain.builder import fixture_to_model_call
from tinkercad_brain.fase0.metrics import compare_connectivity
from tinkercad_brain.fase0.normalize import normalize_circuit
from tinkercad_brain.fase0.probe import ProbeStep, run_steps

__all__ = ["run_build"]

_THINGS_RE = re.compile(r"/things/([^/]+)")


def _parse_json_dict(output) -> dict:
    try:
        parsed = json.loads(output)
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _parse_circuit_id(output) -> str:
    data = _parse_json_dict(output)
    if not data:
        return ""
    for key in ("circuit_id", "circuitId", "id"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, int):
            return str(value)
    nested = data.get("circuit")
    if isinstance(nested, dict):
        for key in ("circuit_id", "circuitId", "id"):
            value = nested.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    url = data.get("url")
    if isinstance(url, str):
        match = _THINGS_RE.search(url)
        if match:
            return match.group(1)
    return ""


def _is_false(value) -> bool:
    if value is False:
        return True
    return isinstance(value, str) and value.strip().casefold() == "false"


def _build_persisted(output) -> bool:
    data = _parse_json_dict(output)
    if not data:
        return True
    return not (_is_false(data.get("success")) or _is_false(data.get("persisted")))


def run_build(fixture: dict, code: str | None, call_tool, title: str) -> dict:
    """Ejecuta un build completo y devuelve el resumen del intento.

    Devuelve {"circuit_id", "url", "fidelity", "serial", "records", "ok"}.
    Si `create` no devuelve un circuit_id parseable, se corta ahi:
    ok=False, sin lanzar y sin llamar al resto de tools.
    """
    records = []

    def _run(tool, arguments):
        step_records = run_steps([ProbeStep(tool=tool, arguments=arguments)], call_tool)
        records.extend(step_records)
        return step_records[0]

    create_record = _run("tinkercad_create_circuit", {"title": title})
    circuit_id = _parse_circuit_id(create_record.output) if create_record.ok else ""
    if not circuit_id:
        return {
            "circuit_id": "",
            "url": "",
            "fidelity": {"score": 0.0},
            "serial": "",
            "records": records,
            "ok": False,
        }

    model_call = fixture_to_model_call(fixture)
    build_record = _run("tinkercad_build_circuit_model", model_call)
    build_ok = _build_persisted(build_record.output)

    if code is not None:
        _run("tinkercad_set_code", {"code": code})

    _run("tinkercad_open_circuit", {"circuit_id_or_url": circuit_id})

    inspect_record = _run("tinkercad_inspect_circuit", {})
    inspect_data = _parse_json_dict(inspect_record.output)
    normalized = normalize_circuit(inspect_data, {"nets": []})
    actual = {
        "components": normalized.get("components", []),
        "nets": derive_nets(inspect_data),
    }
    fidelity = compare_connectivity(fixture, actual)

    _run("tinkercad_start_simulation", {"wait_seconds": 5})
    serial_record = _run("tinkercad_read_serial_monitor", {})
    serial = serial_record.output if serial_record.ok else ""
    _run("tinkercad_stop_simulation", {})

    ok = bool(fidelity.get("score", 0.0) >= 0.99 and build_ok)
    return {
        "circuit_id": circuit_id,
        "url": f"https://www.tinkercad.com/things/{circuit_id}/editel",
        "fidelity": fidelity,
        "serial": serial,
        "records": records,
        "ok": ok,
    }
