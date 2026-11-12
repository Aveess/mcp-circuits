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


_ANALOG_PINS = frozenset(f"A{i}" for i in range(6))


def _validate_pot_pin(pot_pin: str) -> None:
    if pot_pin not in _ANALOG_PINS:
        raise ValueError(f"pot_pin fuera de A0..A5: {pot_pin!r}")


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


# Nota: Servo usa timer1 y analogWrite en 9/10 deja de funcionar al usarla
# (dato real de la skill de netchuu).
def servo_knob_sketch(servo_pin: int = 9, pot_pin: str = "A0") -> str:
    _validate_pin(servo_pin)
    _validate_pot_pin(pot_pin)

    lines = [
        "#include <Servo.h>",
        "",
        "Servo servo;",
        "",
        "void setup() {",
        f"  servo.attach({servo_pin});",
        "  Serial.begin(9600);",
        '  Serial.println("READY");',
        "}",
        "",
        "void loop() {",
        f"  int lectura = analogRead({pot_pin});",
        "  int angulo = map(lectura, 0, 1023, 0, 180);",
        "  servo.write(angulo);",
        '  Serial.print("TEST:ANGLE=");',
        "  Serial.println(angulo);",
        "  delay(50);",
        "}",
    ]
    return "\n".join(lines) + "\n"


def ultrasonic_sketch(trig: int = 7, echo: int = 6) -> str:
    _validate_pin(trig)
    _validate_pin(echo)
    if trig == echo:
        raise ValueError(f"trig y echo deben ser distintos: {trig!r}")

    lines = [
        "void setup() {",
        f"  pinMode({trig}, OUTPUT);",
        f"  pinMode({echo}, INPUT);",
        "  Serial.begin(9600);",
        '  Serial.println("READY");',
        "}",
        "",
        "void loop() {",
        f"  digitalWrite({trig}, LOW);",
        "  delayMicroseconds(2);",
        f"  digitalWrite({trig}, HIGH);",
        "  delayMicroseconds(10);",
        f"  digitalWrite({trig}, LOW);",
        f"  long duracion = pulseIn({echo}, HIGH);",
        "  float distancia = duracion * 0.034 / 2;",
        '  Serial.print("TEST:DIST=");',
        "  Serial.println(distancia);",
        "  delay(200);",
        "}",
    ]
    return "\n".join(lines) + "\n"


def pin_of_fixture(fixture: dict) -> dict:
    """Mapeo {ref_led: pin} segun la cadena uno.D<n> -> rX.1 / rX.2 -> led.anode."""
    pin_by_resistor: dict[str, int] = {}
    leds_by_resistor: dict[str, set[str]] = {}

    for net in fixture.get("nets") or []:
        endpoints = [e for e in net if isinstance(e, str)]
        for a, b in zip(endpoints, endpoints[1:]):
            _scan_pair(a, b, pin_by_resistor, leds_by_resistor)
            _scan_pair(b, a, pin_by_resistor, leds_by_resistor)

    return {
        led: pin_by_resistor[resistor]
        for resistor, leds in leds_by_resistor.items()
        if resistor in pin_by_resistor
        for led in leds
    }


def _scan_pair(a: str, b: str, pin_by_resistor: dict, leds_by_resistor: dict) -> None:
    ref_a, _, pin_a = a.rpartition(".")
    ref_b, _, pin_b = b.rpartition(".")
    if not ref_a or not ref_b:
        return
    match = _UNO_DPIN.match(a)
    if match and pin_b == "1":
        pin_by_resistor[ref_b] = int(match.group(1))
    elif pin_a == "2" and pin_b == "anode":
        leds_by_resistor.setdefault(ref_a, set()).add(ref_b)
