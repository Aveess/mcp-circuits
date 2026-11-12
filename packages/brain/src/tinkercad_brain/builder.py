"""Builder: fixture (components/nets) -> llamada al modelo del puente.

Traduce una fixture a los argumentos de la tool
`tinkercad_build_circuit_model(parts, wires, code)` del puente, donde los
wires son dicts {"from", "to", "color"} de extremos por hueco ("uno.D13",
"1i", "led1.anode" ya traducido a su hueco, etc.), ordenados alimentacion,
tierra y senales para un ruteo ortogonal por carriles estable. El Arduino
no va como part: el puente crea el Uno. Solo stdlib + modulos del proyecto.
"""

from __future__ import annotations

import json
import re

from tinkercad_brain.fase0.component_map import TYPE_MAP
from tinkercad_brain.fase0.probe import ProbeStep, run_steps
from tinkercad_brain.layout import LayoutError, plan_layout

__all__ = ["BuildError", "DID_BY_TYPE", "fixture_to_model_call", "build_circuit"]


class BuildError(Exception):
    """La fixture no puede convertirse en una llamada al modelo completa."""


# Mapa inverso de TYPE_MAP: slug de fixture -> nombre visible en Tinkercad.
_TYPE_BY_SLUG: dict[str, str] = {slug: name for name, slug in TYPE_MAP.items()}

# Tabla DID minima verificada (el puente crea el Uno: arduino-uno no es part).
DID_BY_TYPE: dict[str, int] = {
    "led": 58422,
    "resistor": 53184,
    "pushbutton": 144786,
    "servo": 142073,
    "potentiometer": 45547,
    "tmp36": 112324,
}

# Partes de 3 pines en fila unica: orden fisico (nombre de fixture) y
# nombre real del pin en Tinkercad. El primer pin va en el `at` del
# placement; los demas a +1 y +2 columnas en la misma fila.
_THREE_PIN_PINS: dict[str, tuple[tuple[str, str], ...]] = {
    "servo": (("gnd", "Ground"), ("vcc", "Power"), ("signal", "Signal")),
    "potentiometer": (("1", "term0"), ("2", "wiper"), ("3", "term1")),
    "tmp36": (("vcc", "Vcc"), ("vout", "Vout"), ("gnd", "Gnd")),
}

_HOLE_RE = re.compile(r"([0-9]+)([a-j])")

_POWER_ENDPOINTS = frozenset({"uno.5V", "uno.3V3", "uno.VIN"})
_RAIL_POWER_RE = re.compile(r"[TB]\+(?:[1-9]|[12][0-9]|30)?")
_RAIL_GROUND_RE = re.compile(r"[TB]-(?:[1-9]|[12][0-9]|30)?")
_SIGNAL_PALETTE = (
    "blue", "green", "orange", "yellow", "purple", "turquoise", "pink", "brown",
)


def _wire_group(first: str, second: str) -> int:
    endpoints = (first, second)
    if any(
        e in _POWER_ENDPOINTS or _RAIL_POWER_RE.fullmatch(e) for e in endpoints
    ):
        return 0
    if any(
        e.startswith("uno.GND") or _RAIL_GROUND_RE.fullmatch(e)
        for e in endpoints
    ):
        return 1
    return 2


def _ordered_colored_wires(pairs) -> list[dict[str, str]]:
    grouped: dict[int, list[tuple[str, str]]] = {0: [], 1: [], 2: []}
    for first, second in pairs:
        grouped[_wire_group(first, second)].append((first, second))
    wires = []
    signal_index = 0
    for group in (0, 1, 2):
        for first, second in sorted(grouped[group], key=lambda wire: wire[0]):
            if group == 0:
                color = "red"
            elif group == 1:
                color = "black"
            else:
                color = _SIGNAL_PALETTE[signal_index % len(_SIGNAL_PALETTE)]
                signal_index += 1
            wires.append({"from": first, "to": second, "color": color})
    return wires


def _shift_hole(hole: str, columns: int, endpoint: str) -> str:
    match = _HOLE_RE.fullmatch(hole)
    if match is None:
        raise BuildError(f"hueco de layout invalido {hole!r} para {endpoint!r}")
    column = int(match.group(1)) + columns
    if not 1 <= column <= 30:
        raise BuildError(
            f"hueco derivado fuera de la protoboard para {endpoint!r}: "
            f"{column}{match.group(2)}"
        )
    return f"{column}{match.group(2)}"


def _translate_endpoint(endpoint, placements, type_by_ref) -> str:
    if not isinstance(endpoint, str) or "." not in endpoint:
        raise BuildError(f"extremo de net invalido: {endpoint!r}")
    ref, pin = endpoint.split(".", 1)
    if ref == "uno":
        return endpoint
    placement = placements.get(ref)
    if placement is None:
        raise BuildError(f"extremo sin placement: {endpoint!r}")
    ctype = type_by_ref.get(ref)
    at = placement["at"]
    # Geometria derivada de la receta de layout (ver layout.plan_layout):
    if ctype == "led":
        if pin == "anode":
            return at
        if pin == "cathode":
            return _shift_hole(at, 1, endpoint)
    elif ctype == "resistor":
        if pin == "1":
            return at
        if pin == "2":
            return _shift_hole(at, 4, endpoint)
    elif ctype in _THREE_PIN_PINS:
        for index, (fixture_pin, _real_pin) in enumerate(_THREE_PIN_PINS[ctype]):
            if pin == fixture_pin:
                return at if index == 0 else _shift_hole(at, index, endpoint)
    elif ctype == "pushbutton":
        if pin == "1":
            return at
        # Supuesto explicito: solo se conoce la posicion del pin "1" del
        # boton (en `at`). La geometria completa del pushbutton (pines al
        # otro lado del canal central) aun no esta medida, asi que el
        # resto de pines no se adivina: es BuildError. Esto hace que la
        # fixture boton-pullup (que usa btn1.2) no sea construible todavia.
        raise BuildError(
            f"geometria de pin de pushbutton desconocida: {endpoint!r} "
            f"(solo se conoce el pin '1' en {at})"
        )
    else:
        raise BuildError(
            f"geometria de pines desconocida para {endpoint!r} "
            f"(type {ctype!r} sin receta de huecos)"
        )
    raise BuildError(f"pin sin hueco conocido: {endpoint!r} (type {ctype!r})")


def fixture_to_model_call(fixture: dict, code: str | None = None) -> dict:
    """Convierte una fixture en {"parts", "wires", "code"} para el puente.

    Lanza BuildError si algun componente queda sin layout (no se construye
    a medias), si un type colocado no tiene DID conocido, o si una net usa
    un pin cuya geometria de huecos se desconoce.
    """
    try:
        layout = plan_layout(fixture)
    except LayoutError as exc:
        raise BuildError(str(exc)) from exc

    unplaced = layout["unplaced"]
    if unplaced:
        raise BuildError(
            "sin layout para: " + ", ".join(str(ref) for ref in unplaced)
        )

    placements = layout["placements"]
    type_by_ref = {c["ref"]: c["type"] for c in fixture["components"]}

    parts = []
    for ref, placement in placements.items():
        ctype = type_by_ref.get(ref)
        if ctype not in _TYPE_BY_SLUG:
            raise BuildError(f"type sin nombre conocido para ref {ref!r}: {ctype!r}")
        did = DID_BY_TYPE.get(ctype)
        if did is None:
            raise BuildError(
                f"type sin DID conocido para ref {ref!r}: {ctype!r}"
            )
        part_pin = placement["pin"]
        if ctype in _THREE_PIN_PINS:
            real_by_fixture = dict(_THREE_PIN_PINS[ctype])
            if part_pin not in real_by_fixture:
                raise BuildError(
                    f"pin ancla sin nombre real para ref {ref!r}: "
                    f"{part_pin!r} (type {ctype!r})"
                )
            part_pin = real_by_fixture[part_pin]
        parts.append(
            {
                "ref": ref,
                "did": did,
                "at": placement["at"],
                "pin": part_pin,
                "angle": placement["angle"],
            }
        )

    pairs = []
    for net in fixture.get("nets") or []:
        if not isinstance(net, (list, tuple)) or len(net) < 2:
            raise BuildError(f"net invalida (se esperaban 2+ extremos): {net!r}")
        translated = [
            _translate_endpoint(endpoint, placements, type_by_ref)
            for endpoint in net
        ]
        pairs.extend(zip(translated, translated[1:]))

    return {"parts": parts, "wires": _ordered_colored_wires(pairs), "code": code}


def build_circuit(fixture, code, call_tool) -> dict:
    """Construye el circuito en el puente y luego lo inspecciona.

    El circuito ya debe estar abierto: no se hace open/create. Si el paso
    del modelo devuelve ``success: false`` en su JSON, se registra y se
    devuelve igual (no se lanza).
    """
    model_call = fixture_to_model_call(fixture, code)
    steps = [
        ProbeStep(tool="tinkercad_build_circuit_model", arguments=model_call),
        ProbeStep(tool="tinkercad_inspect_circuit", arguments={}),
    ]
    records = run_steps(steps, call_tool)

    raw = records[0].output if records else ""
    try:
        model_result = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        model_result = raw
    return {"model_result": model_result, "records": records}
