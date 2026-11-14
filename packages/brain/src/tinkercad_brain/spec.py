"""Spec declarativa por huecos de protoboard (portada de netchuu).

Una spec: {"title": str, "parts": [{"ref", "type", "at"|"free", "pin"?,
"angle"?, "props"?}], "wires": [[extremo, extremo]], "code": str}.
Huecos: columnas 1-30, filas a-j ("12e"). Rieles: T+, T-, B+, B- con
columna opcional ("T-12"). Extremos: hueco, riel, "uno.PIN" o "ref.pin".
Solo stdlib.
"""

from __future__ import annotations

import re

try:  # Catálogo canónico existente.
    from tinkercad_brain.fase0.component_map import known_slugs
except ImportError:  # pragma: no cover - import directo sin paquete
    def known_slugs() -> list[str]:  # type: ignore[misc]
        return []

__all__ = ["SpecError", "validate_spec", "KNOWN_TYPES", "PIN_TABLE", "UNO_PINS"]


class SpecError(Exception):
    """La spec no cumple el formato declarativo."""


# Types que aparecen en fixtures/fase0/circuits.json (components[].type).
_FIXTURE_TYPES = {
    "arduino-uno",
    "buzzer",
    "dc-motor",
    "diode",
    "led",
    "led-rgb-common-cathode",
    "photoresistor",
    "potentiometer",
    "pushbutton",
    "resistor",
    "servo",
    "tmp36",
    "transistor-npn",
    "ultrasonic-hcsr04",
}

KNOWN_TYPES = frozenset(_FIXTURE_TYPES | set(known_slugs()))

# Pines por tipo, recolectados de las nets de fixtures/fase0/circuits.json
# (p. ej. "led1.anode", "r1.1", "q1.base"). Claves numéricas como str.
PIN_TABLE: dict[str, frozenset[str]] = {
    "led": frozenset({"anode", "cathode"}),
    "resistor": frozenset({"1", "2"}),
    "pushbutton": frozenset({"1", "2"}),
    "servo": frozenset({"signal", "vcc", "gnd"}),
    "potentiometer": frozenset({"1", "2", "3"}),
    "ultrasonic-hcsr04": frozenset({"vcc", "gnd", "trig", "echo"}),
    "buzzer": frozenset({"positive", "negative"}),
    "photoresistor": frozenset({"1", "2"}),
    "dc-motor": frozenset({"positive", "negative"}),
    "transistor-npn": frozenset({"base", "emitter", "collector"}),
    "diode": frozenset({"anode", "cathode"}),
    "led-rgb-common-cathode": frozenset({"red", "green", "blue", "cathode"}),
    "tmp36": frozenset({"vcc", "vout", "gnd"}),
    # Display 7 segmentos (did 129710): un digito + punto decimal y los dos
    # comunes. En la practica solo se cablea com1 (com2 comparte etiqueta
    # "Common" en el guardado y rompe la conectividad).
    "seven-segment": frozenset(
        {"a", "b", "c", "d", "e", "f", "g", "dp", "com1", "com2"}
    ),
    # 74HC595 (did 116695): 8 salidas + 8 pines de control/alimentacion.
    "shift-register": frozenset(
        {"Q0", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q7S",
         "DS", "SHCP", "STCP", "OE", "MR", "Vcc", "GND"}
    ),
    # Compuertas logicas de 14 pines (74HC86 XOR, 74HC00 NAND): cuatro
    # compuertas de 2 entradas + alimentacion. Los nombres son los del
    # catalogo (1A/1B/1Y ...).
    "xor-gate": frozenset(
        {"1A", "1B", "1Y", "2A", "2B", "2Y", "3A", "3B", "3Y",
         "4A", "4B", "4Y", "Vcc", "GND"}
    ),
    "nand-gate": frozenset(
        {"1A", "1B", "1Y", "2A", "2B", "2Y", "3A", "3B", "3Y",
         "4A", "4B", "4Y", "Vcc", "GND"}
    ),
    # 74HC74 (did 116725): dos biestables D con preset y reset activos en
    # bajo; Q y NQ por cada mitad.
    "flip-flop-d": frozenset(
        {"1D", "1CP", "1RD", "1SD", "1Q", "1NQ",
         "2D", "2CP", "2RD", "2SD", "2Q", "2NQ", "Vcc", "GND"}
    ),
    # 555 Timer (did 116689): 8 pines del DIP.
    "timer-555": frozenset(
        {"CTRL", "Reset", "OUT", "THR", "GND", "DIS", "TRIG", "Vcc"}
    ),
    # Capacitor (did 57752): dos terminales sin polaridad.
    "capacitor": frozenset({"1", "2"}),
    # 74HC93 (did 116728): contador binario de 4 bits, dos resets y dos
    # relojes. Los pines nc1..nc4 del DIP no se cablean.
    "binary-counter": frozenset(
        {"CP0", "CP1", "MR1", "MR2", "Q0", "Q1", "Q2", "Q3", "Vcc", "GND"}
    ),
    # Relay SPDT (did 122167): dos polos; COM1-R1 abierto, COM2-R2 cerrado.
    "relay-spdt": frozenset({"COIL1", "COIL2", "COM1", "R1", "COM2", "R2"}),
    # Bombilla (did 116693): dos terminales sin polaridad.
    "light-bulb": frozenset({"1", "2"}),
    # 74HC4017 (did 129343): contador Johnson de 10 salidas. Q5-9n es el
    # acarreo; CP1n habilita en bajo y MR resetea en alto.
    "decade-counter": frozenset(
        {"CP0", "CP1n", "MR", "Q0", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6",
         "Q7", "Q8", "Q9", "Q5-9n", "Vcc", "GND"}
    ),
    # LCD 16x2 (did 113878): 16 terminales en una fila.
    "lcd-16x2": frozenset(
        {"GND", "VDD", "VO", "RS", "RW", "E",
         "DB0", "DB1", "DB2", "DB3", "DB4", "DB5", "DB6", "DB7",
         "LED+", "LED-"}
    ),
}
# Supuesto: "arduino-uno" y "breadboard" no tienen evidencia de pines en las
# nets de las fixtures (uno se referencia como "uno.PIN", no como ref.pin);
# para esos tipos se acepta cualquier pin no vacío.

UNO_PINS = frozenset(
    [f"D{i}" for i in range(14)]
    + [f"A{i}" for i in range(6)]
    + ["5V", "3V3", "VIN", "GND1", "GND2", "GND3",
       "AREF", "IOREF", "RESET", "SDA", "SCL"]
)

_MAX_PARTS = 60
_MAX_WIRES = 150

_REF_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_HOLE_RE = re.compile(r"(?:[1-9]|[12][0-9]|30)[a-j]")
_RAIL_RE = re.compile(r"[TB][+-](?:[1-9]|[12][0-9]|30)?")


def _is_hole(value: object) -> bool:
    return isinstance(value, str) and _HOLE_RE.fullmatch(value) is not None


def _is_rail(value: object) -> bool:
    return isinstance(value, str) and _RAIL_RE.fullmatch(value) is not None


def _check_pin(pin: object, type_: str, where: str) -> None:
    # Acepta pines numéricos dados como int (p. ej. 1 -> "1").
    if isinstance(pin, bool):
        raise SpecError(f"{where}: pin inválido {pin!r}")
    name = str(pin) if isinstance(pin, int) else pin
    if not isinstance(name, str) or not name.strip():
        raise SpecError(f"{where}: pin inválido {pin!r} para type '{type_}'")
    known = PIN_TABLE.get(type_)
    if known is not None and name not in known:
        raise SpecError(
            f"{where}: pin desconocido '{name}' para type '{type_}'"
        )


def _validate_endpoint(endpoint: object, ref_types: dict[str, str]) -> None:
    if not isinstance(endpoint, str) or not endpoint:
        raise SpecError(f"wire: extremo inválido {endpoint!r}")
    if "." in endpoint:
        head, _, pin = endpoint.partition(".")
        if not head or not pin or "." in pin:
            raise SpecError(f"wire: extremo inválido '{endpoint}'")
        if head == "uno":
            if pin not in UNO_PINS:
                raise SpecError(
                    f"wire: pin de uno inválido '{pin}' en '{endpoint}'"
                )
            return
        if head not in ref_types:
            raise SpecError(f"wire: ref no declarado '{head}' en '{endpoint}'")
        _check_pin(pin, ref_types[head], "wire")
        return
    if not (_is_hole(endpoint) or _is_rail(endpoint)):
        raise SpecError(f"wire: extremo inválido '{endpoint}'")


def validate_spec(spec: dict) -> dict:
    """Valida `spec` y devuelve la copia normalizada.

    Los wires quedan como lista de {"from": ..., "to": ...}.
    Lanza SpecError con mensaje claro ante cualquier rechazo.
    """
    if not isinstance(spec, dict):
        raise SpecError("spec: debe ser un dict")

    if "title" in spec and not isinstance(spec["title"], str):
        raise SpecError(f"title: debe ser str, no {spec['title']!r}")
    if "code" in spec and not isinstance(spec["code"], str):
        raise SpecError(f"code: debe ser str, no {spec['code']!r}")

    if "parts" not in spec or not isinstance(spec["parts"], list):
        raise SpecError("parts: falta 'parts' o no es una lista")
    parts = spec["parts"]
    if len(parts) > _MAX_PARTS:
        raise SpecError(f"parts: más de {_MAX_PARTS} parts ({len(parts)})")

    wires_in = spec.get("wires", [])
    if not isinstance(wires_in, list):
        raise SpecError("wires: 'wires' no es una lista")
    if len(wires_in) > _MAX_WIRES:
        raise SpecError(f"wires: más de {_MAX_WIRES} wires ({len(wires_in)})")

    ref_types: dict[str, str] = {}
    seen_at: dict[str, str] = {}
    for i, part in enumerate(parts):
        where = f"parts[{i}]"
        if not isinstance(part, dict):
            raise SpecError(f"{where}: cada part debe ser un dict")
        ref = part.get("ref")
        if ref == "uno":
            raise SpecError("ref 'uno' está reservado para el Arduino")
        if not isinstance(ref, str) or _REF_RE.fullmatch(ref) is None:
            raise SpecError(f"{where}: ref inválido {ref!r}")
        if ref in ref_types:
            raise SpecError(f"ref duplicado: '{ref}'")
        type_ = part.get("type")
        if not isinstance(type_, str) or type_ not in KNOWN_TYPES:
            raise SpecError(f"{where} ('{ref}'): type desconocido {type_!r}")
        ref_types[ref] = type_

        if "at" in part and "free" in part:
            raise SpecError(
                f"{where} ('{ref}'): 'at' y 'free' son excluyentes"
            )
        if "angle" in part:
            angle = part["angle"]
            if (
                isinstance(angle, bool)
                or not isinstance(angle, int)
                or angle not in (0, 90, 180, 270)
            ):
                raise SpecError(
                    f"{where} ('{ref}'): angle inválido {angle!r} "
                    "(esperado uno de 0, 90, 180, 270)"
                )
        if "at" in part and not (_is_hole(part["at"]) or _is_rail(part["at"])):
            raise SpecError(
                f"{where} ('{ref}'): at inválido {part['at']!r} "
                "(esperado hueco '12e' o riel 'T-12')"
            )
        if "at" in part:
            if part["at"] in seen_at:
                raise SpecError(
                    f"{where} ('{ref}'): at {part['at']!r} ya ocupado por "
                    f"'{seen_at[part['at']]}' (colisión)"
                )
            seen_at[part["at"]] = ref
        if "free" in part:
            free = part["free"]
            if (
                not isinstance(free, dict)
                or set(free) != {"x", "y"}
                or any(
                    isinstance(v, bool) or not isinstance(v, (int, float))
                    for v in free.values()
                )
            ):
                raise SpecError(
                    f"{where} ('{ref}'): free inválido {free!r} "
                    "(esperado {'x': n, 'y': n})"
                )
        if "at" not in part and "free" not in part:
            raise SpecError(f"{where} ('{ref}'): falta 'at' o 'free'")
        if "pin" in part:
            _check_pin(part["pin"], type_, where)

    wires: list[dict[str, object]] = []
    for i, wire in enumerate(wires_in):
        if isinstance(wire, dict):
            if "from" not in wire or "to" not in wire:
                raise SpecError(f"wire[{i}]: wire sin 'from'/'to': {wire!r}")
            pair = (wire["from"], wire["to"])
        elif isinstance(wire, (list, tuple)) and len(wire) == 2:
            pair = (wire[0], wire[1])
        else:
            raise SpecError(
                f"wire[{i}]: wire inválido {wire!r} (esperado par de extremos)"
            )
        for endpoint in pair:
            _validate_endpoint(endpoint, ref_types)
        wires.append({"from": pair[0], "to": pair[1]})

    normalized = dict(spec)
    normalized["parts"] = [dict(part) for part in parts]
    normalized["wires"] = wires
    return normalized
