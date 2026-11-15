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
import time

from tinkercad_brain.breadboard_nets import derive_nets
from tinkercad_brain.builder import (
    diagonal_segments,
    fixture_to_model_call,
    route_band_violations,
)
from tinkercad_brain.fase0.metrics import compare_connectivity
from tinkercad_brain.fase0.normalize import normalize_circuit
from tinkercad_brain.fase0.probe import ProbeStep, run_steps
from tinkercad_brain.oracle import check_serial

__all__ = ["run_build"]

_THINGS_RE = re.compile(r"/things/([^/]+)")

# Lectura del circuito tras reconstruirlo. `inspect_circuit` puede devolver 0
# componentes y 0 cables mientras la pagina se recarga (medido en vivo con
# blink-basico: el segundo inspect ya traia 4 componentes y 10 cables). Eso
# no es un circuito vacio, es una lectura que no llego: reintentar antes de
# acusar un 0%.
READ_ATTEMPTS = 3
READ_RETRY_SLEEP = 1.5

# Espera del oraculo: `sim_wait_seconds` es reloj de pared y el simulador
# arranca a una fraccion de la velocidad real, asi que tras la primera ventana
# se sondea el serial hasta que aparezcan todas las marcas. El tope evita que
# un sketch de verdad roto cueste una eternidad.
ORACLE_PATIENCE_S = 150.0
ORACLE_POLL_S = 10.0


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


def _refs_by_name(output) -> dict[str, str]:
    """{nombre real en el documento: ref de la fixture} del resultado del build.

    ``placed[ref].name`` lo escribe el puente leyendo el nombre despues de
    asignarlo. Si el build no lo trae (puente viejo), queda vacio y el
    verificador sigue con el criterio anterior (nombre del inspect).
    """
    placed = _parse_json_dict(output).get("placed")
    if not isinstance(placed, dict):
        return {}
    refs = {}
    for ref, info in placed.items():
        if not isinstance(info, dict):
            continue
        name = info.get("name")
        if isinstance(name, str) and name.strip():
            refs[name.strip()] = ref
    return refs


def _build_persisted(output) -> bool:
    data = _parse_json_dict(output)
    if not data:
        return True
    return not (_is_false(data.get("success")) or _is_false(data.get("persisted")))


def _success_false(output) -> bool:
    return _is_false(_parse_json_dict(output).get("success"))


def _circuit_id_from_entry(entry: dict) -> str:
    for key in ("circuit_id", "circuitId", "id"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, int):
            return str(value)
    url = entry.get("url")
    if isinstance(url, str):
        match = _THINGS_RE.search(url)
        if match:
            return match.group(1)
    return ""


def _normalize_title(value) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[\s\-_]+", "", value.casefold())


def _find_reusable_circuit(output, title: str) -> str:
    searched = _normalize_title(title)
    if not searched:
        return ""
    try:
        parsed = json.loads(output)
    except (json.JSONDecodeError, TypeError, ValueError):
        return ""
    candidates = None
    if isinstance(parsed, list):
        candidates = parsed
    elif isinstance(parsed, dict):
        for key in ("circuits", "items", "data", "results"):
            if isinstance(parsed.get(key), list):
                candidates = parsed[key]
                break
    if not candidates:
        return ""
    for exact in (True, False):
        for entry in candidates:
            if not isinstance(entry, dict):
                continue
            returned = _normalize_title(entry.get("title") or entry.get("name"))
            if not returned:
                continue
            matched = searched == returned if exact else searched in returned
            if matched:
                circuit_id = _circuit_id_from_entry(entry)
                if circuit_id:
                    return circuit_id
    return ""


def run_build(
    fixture: dict,
    code: str | None,
    call_tool,
    title: str,
    presets=None,
    repair: bool = True,
    reuse: bool = True,
    preferred_id: str = "",
) -> dict:
    """Ejecuta un build completo y devuelve el resumen del intento.

    Devuelve {"circuit_id", "url", "fidelity", "serial", "records", "ok",
    "repair_attempted", "fidelity_before_repair", "reused"}.
    Si `create` no devuelve un circuit_id parseable, se corta ahi:
    ok=False, sin lanzar y sin llamar al resto de tools.

    Con `preferred_id` no vacio se reutiliza ese circuito directamente, sin
    listar ni buscar por titulo: es el `tinkercad_id` que guarda la fixture y
    lo unico que evita duplicados cuando el diseno se renombra en Tinkercad.

    Con `reuse=True` (defecto), antes de crear se lista la cuenta y, si un
    circuito coincide con `title`, se reutiliza: se abre ese circuito y el
    build lleva ``clear_existing: True`` (reemplazo limpio). Si la lista
    falla o no parsea, se cae a crear como siempre, sin lanzar. Con
    `reuse=False` siempre se crea un circuito nuevo.

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

    circuit_id = ""
    reused = False
    already_open = False
    if reuse:
        # `preferred_id` (el `tinkercad_id` de la fixture, que pasa
        # demo_build) manda: un circuito ya construido se reusa por id aunque
        # el titulo del diseno y el de la fixture no coincidan. Con el match
        # por titulo salian duplicados cada vez que el diseno se renombraba
        # en Tinkercad (paso con motor-dc-transistor).
        pinned_id = str(preferred_id or "").strip()
        if pinned_id:
            open_record = _run(
                "tinkercad_open_circuit", {"circuit_id_or_url": pinned_id}
            )
            if open_record.ok and not _success_false(open_record.output):
                circuit_id = pinned_id
                reused = True
                already_open = True
        if not reused:
            list_record = _run("tinkercad_list_circuits", {})
            if list_record.ok:
                circuit_id = _find_reusable_circuit(list_record.output, title)
            reused = bool(circuit_id)

    if reused and not already_open:
        open_record = _run("tinkercad_open_circuit", {"circuit_id_or_url": circuit_id})
        if not open_record.ok or _success_false(open_record.output):
            reused = False
            circuit_id = ""
    if not reused:
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
                "reused": False,
                "route_violations": [],
                "diagonal_violations": [],
                "board_hop_diagonals": [],
                "routes": {"routed": 0, "measured": 0},
                "checks": {},
            }

    model_call = fixture_to_model_call(fixture)
    model_call["clear_existing"] = reused
    # La reparacion reenvia solo los cables: no puede reconstruir una parte
    # libre (LCD, 7 segmentos), porque clear_existing borro el dispositivo y
    # sin `parts` los terminales no resuelven. En esos casos se reconstruye
    # completo en vez de reparar.
    has_free_parts = any(
        isinstance(part, dict) and "free" in part
        for part in model_call.get("parts", [])
    )
    build_record = _run("tinkercad_build_circuit_model", model_call)
    build_ok = _build_persisted(build_record.output)
    build_success_false = _success_false(build_record.output)
    # Nombre real que el editor dejo en cada parte -> ref de la fixture. Es
    # la unica identidad fiable: Tinkercad deduplica (setName("r2") con otro
    # "r2" en el documento deja "r21"), asi que el verificador no puede
    # suponer que el nombre es la ref (fase 39).
    refs_by_name = _refs_by_name(build_record.output)
    name_by_ref = {ref: name for name, ref in refs_by_name.items()}
    # Regla 3 de organizacion-cables medida: ningun tramo horizontal sobre el
    # cuerpo de una placa. El puente devuelve la polilinea de cada cable.
    routes = _parse_json_dict(build_record.output).get("route_debug") or []
    route_violations = route_band_violations(routes, model_call.get("boards"))
    # Regla 4: un cable que toca una parte libre o el Uno no puede quedar en
    # diagonal (asi se veia "torcido" el circuito 28). Los saltos rectos
    # entre huecos de la placa se cuentan pero no rompen el build.
    free_refs = [
        part.get("ref")
        for part in model_call.get("parts", [])
        if isinstance(part, dict) and part.get("free") is not None
    ]
    diagonals = diagonal_segments(routes, free_refs)
    diagonal_violations = [d for d in diagonals if d.get("blocking")]
    board_hop_diagonals = [d for d in diagonals if not d.get("blocking")]
    # Cuantos cables se midieron de verdad: sin esto un "0 cruces" podria
    # significar que no llego ninguna polilinea.
    routes_routed = sum(1 for r in routes if isinstance(r, dict) and r.get("routed"))
    routes_measured = sum(
        1 for r in routes
        if isinstance(r, dict) and r.get("points")
    )
    routes_total = len(model_call.get("wires") or [])

    preset_reported_failure = False
    for preset in presets or []:
        preset_args = {
            # El preset nombra refs de la fixture, pero el editor puede haber
            # dejado otro nombre (deduplicacion); se resuelve con el mapa del
            # build. Un preset por tipo ("Resistor") pasa tal cual.
            "component_name": name_by_ref.get(
                preset.get("component"), preset.get("component")
            ),
            "property_name": preset.get("property"),
            "value": preset.get("value"),
        }
        # El cuarto argumento del modelo es el prefijo (k, u, n...), no la
        # unidad completa. Solo se envia cuando la fixture lo pide, para no
        # cambiar la forma de los presets que ya existen.
        if preset.get("unit") is not None:
            preset_args["unit"] = preset["unit"]
        preset_record = _run(
            "tinkercad_set_component_property_model",
            preset_args,
        )
        if _success_false(preset_record.output):
            preset_record.ok = False
            preset_reported_failure = True

    if code is not None:
        _run("tinkercad_set_code", {"code": code})

    def _measure():
        _run("tinkercad_open_circuit", {"circuit_id_or_url": circuit_id})
        # Solo un build que dice haber aplicado se puede leer vacio. Si el
        # build fallo, el circuito puede estar vacio de verdad y culpar a la
        # lectura seria cambiar una causa por otra.
        expected_components = len(fixture.get("components") or []) if build_ok else 0
        attempts = 0
        read_failed = False
        read_reason = None
        read_editor_state = {}
        inspect_data = {}
        while True:
            attempts += 1
            inspect_record = _run("tinkercad_inspect_circuit", {})
            inspect_data = _parse_json_dict(inspect_record.output)
            read_components = len(inspect_data.get("components") or [])
            if read_components or not expected_components:
                break
            if attempts >= READ_ATTEMPTS:
                # Se agotaron los intentos con la fixture esperando partes:
                # esto es "no pude leer", no "el circuito esta mal".
                read_failed = True
                break
            time.sleep(READ_RETRY_SLEEP)
        # Si el editor no monto, el "vacio" tiene causa y hay que nombrarla:
        # sin esto el reporte dice "no se pudo leer" y deja creer que el
        # cableado esta mal.
        if inspect_data.get("reason"):
            read_reason = str(inspect_data["reason"])
            read_editor_state = inspect_data.get("editor_state") or {}
        normalized = normalize_circuit(inspect_data, {"nets": []}, refs_by_name)
        actual = {
            "components": normalized.get("components", []),
            "nets": derive_nets(inspect_data, refs_by_name),
        }
        fidelity = compare_connectivity(fixture, actual)
        fidelity["read_attempts"] = attempts
        fidelity["read_failed"] = read_failed
        if read_reason:
            fidelity["read_reason"] = read_reason
            fidelity["editor_state"] = read_editor_state
        return fidelity

    fidelity = _measure()

    repair_attempted = False
    fidelity_before_repair = None
    repair_ok = True
    if (
        repair
        and not has_free_parts
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

    # La ventana de simulacion es 5 s por defecto; una fixture puede pedir
    # mas con "sim_wait_seconds" cuando su oraculo necesita varios ciclos
    # (p. ej. el contador de 2 Hz tarda en arrancar el simulador).
    wait_seconds = fixture.get("sim_wait_seconds", 5)
    sim_record = _run("tinkercad_start_simulation", {"wait_seconds": wait_seconds})

    expected_serial = [str(m) for m in (fixture.get("oracle_serial") or []) if str(m)]
    serial_record = _run("tinkercad_read_serial_monitor", {})
    serial = serial_record.output if serial_record.ok else ""

    # `wait_seconds` es reloj de pared, pero el simulador no arranca a
    # velocidad real: con la placa recien cargada avanza a una fraccion y
    # despues acelera (medido 2026-11-15: 2 s simulados en 55 s reales en el
    # contador, 15 s simulados a los 40 s en una pagina ya asentada). Un
    # unico sleep declara "no funciona" a un sketch que solo iba lento, asi
    # que se sondea el serial hasta que esten todas las marcas, con tope.
    #
    # Solo si esta corrida **escribio** el sketch: sin codigo nuevo las marcas
    # de la fixture no las produce nadie y esperarlas seria dormir por gusto
    # (un test que reusa por id pagaba 150 s por esto).
    if (expected_serial and code and sim_record.ok
            and not _success_false(sim_record.output)):
        limite = time.monotonic() + ORACLE_PATIENCE_S
        while not check_serial(serial, expected_serial)["ok"]:
            if time.monotonic() >= limite:
                break
            time.sleep(ORACLE_POLL_S)
            otra = _run("tinkercad_read_serial_monitor", {})
            if otra.ok and otra.output:
                serial = otra.output

    # El oraculo: que marcas declara la fixture y si el serial las probo.
    # Un sketch que imprime y no dejo nada no es "funciono": es una prueba
    # que falta, y el build no puede salir OK sin comportamiento observado.
    serial_required = bool(expected_serial) or bool(code and "Serial." in code)
    if serial_required and not serial.strip():
        # El monitor puede engancharse un instante tarde; una segunda
        # lectura mientras simula es barata y evita acusar por una carrera.
        time.sleep(1.0)
        retry_record = _run("tinkercad_read_serial_monitor", {})
        if retry_record.ok:
            serial = retry_record.output or serial
    serial_check = check_serial(serial, expected_serial)
    _run("tinkercad_stop_simulation", {})

    ok = bool(
        fidelity.get("score", 0.0) >= 0.99
        and not fidelity.get("read_failed")
        and build_ok
        and repair_ok
        and not preset_reported_failure
        and not route_violations
        and not diagonal_violations
        and serial_check["ok"]
        and (bool(serial.strip()) if serial_required else True)
    )
    # Por que el build no esta OK: sin esto un "OK: False" con fidelidad 100%
    # y cero cruces no dice nada y hay que adivinar.
    checks = {
        "fidelity": fidelity.get("score", 0.0),
        # Una lectura vacia con partes esperadas es "no se pudo leer", no un
        # circuito mal armado: se nombra aparte para no reportar un cero mudo.
        "fidelity_readable": not fidelity.get("read_failed", False),
        "read_reason": fidelity.get("read_reason"),
        "build_ok": build_ok,
        "repair_ok": repair_ok,
        "presets_ok": not preset_reported_failure,
        "route_violations": len(route_violations),
        "diagonals": len(diagonal_violations),
        # Contrato del oraculo: las marcas declaradas tienen que aparecer en
        # orden, y si el sketch imprime, el serial no puede venir vacio.
        "oracle_ok": serial_check["ok"],
        "oracle_missing": serial_check["missing"],
        "oracle_expected": expected_serial,
        "serial_nonempty": (bool(serial.strip()) if serial_required else True),
        "serial_lines": len([ln for ln in serial.splitlines() if ln.strip()]),
        "build_errors": [
            str(e) for e in (_parse_json_dict(build_record.output).get("errors") or [])
        ][:5],
    }
    return {
        "circuit_id": circuit_id,
        "url": f"https://www.tinkercad.com/things/{circuit_id}/editel",
        "fidelity": fidelity,
        "serial": serial,
        "records": records,
        "ok": ok,
        "repair_attempted": repair_attempted,
        "fidelity_before_repair": fidelity_before_repair,
        "reused": reused,
        "route_violations": route_violations,
        "diagonal_violations": diagonal_violations,
        "board_hop_diagonals": board_hop_diagonals,
        "routes": {"routed": routes_routed, "measured": routes_measured,
                   "total": routes_total},
        "oracle": {
            "expected": expected_serial,
            "found": serial_check["found"],
            "missing": serial_check["missing"],
            "ok": serial_check["ok"],
            "serial_required": serial_required,
            "serial_lines": len([ln for ln in serial.splitlines() if ln.strip()]),
        },
        "checks": checks,
    }
