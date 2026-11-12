"""Sketches Arduino deterministas e instrumentados por serial.

Dos plantillas honestas (blink y semaforo), no un generador general.
El pin se emite como literal en pinMode/digitalWrite y, si hay serial,
cada fase deja una traza ``TEST:...`` observable (v2, seccion 10.2).
"""

from __future__ import annotations

import re

_PIN_MIN, _PIN_MAX = 2, 13
_MS_MIN, _MS_MAX = 1, 60000

_UNO_DPIN = re.compile(r"^uno\.D(\d+)$")


def _validate_pin(pin: int) -> None:
    if not isinstance(pin, int) or isinstance(pin, bool) or not _PIN_MIN <= pin <= _PIN_MAX:
        raise ValueError(f"pin fuera de {_PIN_MIN}..{_PIN_MAX}: {pin!r}")


def _validate_ms(name: str, value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or not _MS_MIN <= value <= _MS_MAX:
        raise ValueError(f"{name} fuera de {_MS_MIN}..{_MS_MAX} ms: {value!r}")


def blink_sketch(pin: int = 13, on_ms: int = 500, off_ms: int = 500, serial: bool = True) -> str:
    _validate_pin(pin)
    _validate_ms("on_ms", on_ms)
    _validate_ms("off_ms", off_ms)

    setup = ["void setup() {", f"  pinMode({pin}, OUTPUT);"]
    if serial:
        setup += ["  Serial.begin(9600);", '  Serial.println("READY");']
    setup.append("}")

    loop = ["void loop() {", f"  digitalWrite({pin}, HIGH);"]
    if serial:
        loop.append('  Serial.println("TEST:ON");')
    loop.append(f"  delay({on_ms});")
    loop.append(f"  digitalWrite({pin}, LOW);")
    if serial:
        loop.append('  Serial.println("TEST:OFF");')
    loop.append(f"  delay({off_ms});")
    loop.append("}")

    return "\n".join(setup + [""] + loop) + "\n"


def traffic_sketch(
    red: int = 11,
    yellow: int = 10,
    green: int = 9,
    red_ms: int = 2000,
    yellow_ms: int = 700,
    green_ms: int = 2000,
) -> str:
    for pin in (red, yellow, green):
        _validate_pin(pin)
    if len({red, yellow, green}) != 3:
        raise ValueError(f"pines repetidos en semaforo: red={red}, yellow={yellow}, green={green}")
    _validate_ms("red_ms", red_ms)
    _validate_ms("yellow_ms", yellow_ms)
    _validate_ms("green_ms", green_ms)

    pins = (red, yellow, green)
    phases = (
        ("RED", red, red_ms),
        ("YELLOW", yellow, yellow_ms),
        ("GREEN", green, green_ms),
    )

    lines = [
        "void setup() {",
        f"  pinMode({red}, OUTPUT);",
        f"  pinMode({yellow}, OUTPUT);",
        f"  pinMode({green}, OUTPUT);",
        "  Serial.begin(9600);",
        '  Serial.println("READY");',
        "}",
        "",
        "void loop() {",
    ]
    for name, active, duration in phases:
        for pin in pins:
            lines.append(f"  digitalWrite({pin}, {'HIGH' if pin == active else 'LOW'});")
        lines.append(f'  Serial.println("TEST:{name}");')
        lines.append(f"  delay({duration});")
    lines.append("}")
    return "\n".join(lines) + "\n"


def pin_of_fixture(fixture: dict) -> dict:
    """Mapeo {ref_led: pin} segun la cadena uno.D<n> -> rX.1 / rX.2 -> led.anode."""
    pin_by_resistor: dict[str, int] = {}
    led_by_resistor: dict[str, str] = {}

    for net in fixture.get("nets") or []:
        endpoints = [e for e in net if isinstance(e, str)]
        for a, b in zip(endpoints, endpoints[1:]):
            _scan_pair(a, b, pin_by_resistor, led_by_resistor)
            _scan_pair(b, a, pin_by_resistor, led_by_resistor)

    return {
        led: pin_by_resistor[resistor]
        for resistor, led in led_by_resistor.items()
        if resistor in pin_by_resistor
    }


def _scan_pair(a: str, b: str, pin_by_resistor: dict, led_by_resistor: dict) -> None:
    ref_a, _, pin_a = a.rpartition(".")
    ref_b, _, pin_b = b.rpartition(".")
    if not ref_a or not ref_b:
        return
    match = _UNO_DPIN.match(a)
    if match and pin_b == "1":
        pin_by_resistor[ref_b] = int(match.group(1))
    elif pin_a == "2" and pin_b == "anode":
        led_by_resistor[ref_a] = ref_b
