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


def _success_false(output) -> bool:
    return _is_false(_parse_json_dict(output).get("success"))


def run_build(
    fixture: dict,
    code: str | None,
    call_tool,
    title: str,
    presets=None,
    repair: bool = True,
) -> dict:
    """Ejecuta un build completo y devuelve el resumen del intento.

    Devuelve {"circuit_id", "url", "fidelity", "serial", "records", "ok",
    "repair_attempted", "fidelity_before_repair"}.
    Si `create` no devuelve un circuit_id parseable, se corta ahi:
    ok=False, sin lanzar y sin llamar al resto de tools.

    `presets`: lista opcional de {"component", "property", "value"} que se
    aplica tras el build y antes de recargar; un preset que falla queda en
    `records` y no aborta. Con `repair=True`, si la primera fidelidad es
    < 0.99, no hay cortos y el build no reporto success False, se
    re-cablea una vez (solo wires) y se re-mide.
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
            "repair_attempted": False,
            "fidelity_before_repair": None,
        }

    model_call = fixture_to_model_call(fixture)
    build_record = _run("tinkercad_build_circuit_model", model_call)
    build_ok = _build_persisted(build_record.output)
    build_success_false = _success_false(build_record.output)

    preset_reported_failure = False
    for preset in presets or []:
        preset_record = _run(
            "tinkercad_set_component_property_model",
            {
                "component_name": preset.get("component"),
                "property_name": preset.get("property"),
                "value": preset.get("value"),
            },
        )
        if _success_false(preset_record.output):
            preset_record.ok = False
            preset_reported_failure = True

    if code is not None:
        _run("tinkercad_set_code", {"code": code})

    def _measure():
        _run("tinkercad_open_circuit", {"circuit_id_or_url": circuit_id})
        inspect_record = _run("tinkercad_inspect_circuit", {})
        inspect_data = _parse_json_dict(inspect_record.output)
        normalized = normalize_circuit(inspect_data, {"nets": []})
        actual = {
            "components": normalized.get("components", []),
            "nets": derive_nets(inspect_data),
        }
        return compare_connectivity(fixture, actual)

    fidelity = _measure()

    repair_attempted = False
    fidelity_before_repair = None
    repair_ok = True
    if (
        repair
        and fidelity.get("score", 0.0) < 0.99
        and not fidelity.get("shorts")
        and not build_success_false
    ):
        repair_attempted = True
        fidelity_before_repair = fidelity
        repair_record = _run(
            "tinkercad_build_circuit_model",
            {"parts": [], "wires": model_call.get("wires", [])},
        )
        repair_ok = _build_persisted(repair_record.output)
        fidelity = _measure()

    _run("tinkercad_start_simulation", {"wait_seconds": 5})
    serial_record = _run("tinkercad_read_serial_monitor", {})
    serial = serial_record.output if serial_record.ok else ""
    _run("tinkercad_stop_simulation", {})

    ok = bool(
        fidelity.get("score", 0.0) >= 0.99
        and build_ok
        and repair_ok
        and not preset_reported_failure
    )
    return {
        "circuit_id": circuit_id,
        "url": f"https://www.tinkercad.com/things/{circuit_id}/editel",
        "fidelity": fidelity,
        "serial": serial,
        "records": records,
        "ok": ok,
        "repair_attempted": repair_attempted,
        "fidelity_before_repair": fidelity_before_repair,
    }
