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


_DWELL_MIN, _DWELL_MAX = 50, 60000


def _validate_dwell(value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or not _DWELL_MIN <= value <= _DWELL_MAX:
        raise ValueError(f"dwell_ms fuera de {_DWELL_MIN}..{_DWELL_MAX} ms: {value!r}")


def rgb_cycle_sketch(red: int = 9, green: int = 10, blue: int = 11, dwell_ms: int = 900) -> str:
    for pin in (red, green, blue):
        _validate_pin(pin)
    if len({red, green, blue}) != 3:
        raise ValueError(f"pines repetidos en RGB: red={red}, green={green}, blue={blue}")
    _validate_dwell(dwell_ms)

    pins = (red, green, blue)
    phases = (
        ("RED", red),
        ("GREEN", green),
        ("BLUE", blue),
    )

    lines = [
        "void setup() {",
        f"  pinMode({red}, OUTPUT);",
        f"  pinMode({green}, OUTPUT);",
        f"  pinMode({blue}, OUTPUT);",
        "  Serial.begin(9600);",
        '  Serial.println("READY");',
        "}",
        "",
        "void loop() {",
    ]
    for name, active in phases:
        for pin in pins:
            lines.append(f"  digitalWrite({pin}, {'HIGH' if pin == active else 'LOW'});")
        lines.append(f'  Serial.println("TEST:COLOR={name}");')
        lines.append(f"  delay({dwell_ms});")
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


_DIST_THRESHOLD_MIN, _DIST_THRESHOLD_MAX = 2.0, 400.0


def _validate_threshold_cm(threshold_cm: float) -> None:
    if (
        not isinstance(threshold_cm, (int, float))
        or isinstance(threshold_cm, bool)
        or not _DIST_THRESHOLD_MIN <= threshold_cm <= _DIST_THRESHOLD_MAX
    ):
        raise ValueError(
            f"threshold_cm fuera de {_DIST_THRESHOLD_MIN}..{_DIST_THRESHOLD_MAX}: {threshold_cm!r}"
        )


def ultrasonic_sketch(trig: int = 7, echo: int = 6, led_pin: int = 13, threshold_cm: float = 40.0) -> str:
    _validate_pin(trig)
    _validate_pin(echo)
    _validate_pin(led_pin)
    if len({trig, echo, led_pin}) != 3:
        raise ValueError(f"pines repetidos en ultrasonico: trig={trig}, echo={echo}, led_pin={led_pin}")
    _validate_threshold_cm(threshold_cm)
    threshold_text = _format_threshold(threshold_cm)

    lines = [
        "void setup() {",
        f"  pinMode({trig}, OUTPUT);",
        f"  pinMode({echo}, INPUT);",
        f"  pinMode({led_pin}, OUTPUT);",
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
        f"  digitalWrite({led_pin}, distancia < {threshold_text} ? HIGH : LOW);",
        '  Serial.print("TEST:DIST=");',
        "  Serial.println(distancia);",
        f'  Serial.println(distancia < {threshold_text} ? "TEST:LED=ON" : "TEST:LED=OFF");',
        "  delay(200);",
        "}",
    ]
    return "\n".join(lines) + "\n"


_THRESHOLD_MIN, _THRESHOLD_MAX = -40.0, 125.0


def _validate_threshold(threshold: float) -> None:
    if (
        not isinstance(threshold, (int, float))
        or isinstance(threshold, bool)
        or not _THRESHOLD_MIN <= threshold <= _THRESHOLD_MAX
    ):
        raise ValueError(f"threshold fuera de {_THRESHOLD_MIN}..{_THRESHOLD_MAX}: {threshold!r}")


def _format_threshold(threshold: float) -> str:
    text = f"{float(threshold):f}".rstrip("0")
    return text + "0" if text.endswith(".") else text


def tmp36_sketch(pin: int = 13, analog_pin: str = "A0", threshold: float = 20.0) -> str:
    _validate_pin(pin)
    _validate_pot_pin(analog_pin)
    _validate_threshold(threshold)

    lines = [
        "void setup() {",
        f"  pinMode({pin}, OUTPUT);",
        "  Serial.begin(9600);",
        '  Serial.println("READY");',
        "}",
        "",
        "void loop() {",
        f"  int lectura = analogRead({analog_pin});",
        "  float volts = lectura * 5.0/1023.0;",
        "  float temp = (volts - 0.5) * 100.0;",
        '  Serial.print("TEST:TEMP=");',
        "  Serial.println(temp);",
        f"  digitalWrite({pin}, temp > {_format_threshold(threshold)} ? HIGH : LOW);",
        "  delay(500);",
        "}",
    ]
    return "\n".join(lines) + "\n"


def motor_sketch(pin: int = 9) -> str:
    _validate_pin(pin)

    lines = [
        "void setup() {",
        f"  pinMode({pin}, OUTPUT);",
        "  Serial.begin(9600);",
        '  Serial.println("READY");',
        "}",
        "",
        "void loop() {",
        f"  digitalWrite({pin}, HIGH);",
        '  Serial.println("TEST:MOTOR=ON");',
        "  delay(2000);",
        f"  digitalWrite({pin}, LOW);",
        '  Serial.println("TEST:MOTOR=OFF");',
        "  delay(1000);",
        "}",
    ]
    return "\n".join(lines) + "\n"


def motor_driver_sketch(enable_pin: int = 9, in1: int = 7, in2: int = 8, pot_pin: str = "A0") -> str:
    for pin in (enable_pin, in1, in2):
        _validate_pin(pin)
    if len({enable_pin, in1, in2}) != 3:
        raise ValueError(f"pines repetidos en driver: enable_pin={enable_pin}, in1={in1}, in2={in2}")
    _validate_pot_pin(pot_pin)

    lines = [
        "void setup() {",
        f"  pinMode({enable_pin}, OUTPUT);",
        f"  pinMode({in1}, OUTPUT);",
        f"  pinMode({in2}, OUTPUT);",
        "  Serial.begin(9600);",
        '  Serial.println("READY");',
        "}",
        "",
        "void loop() {",
        f"  int lectura = analogRead({pot_pin});",
        "  int velocidad = map(lectura, 0, 1023, 0, 255);",
        f"  digitalWrite({in1}, HIGH);",
        f"  digitalWrite({in2}, LOW);",
        f"  analogWrite({enable_pin}, velocidad);",
        '  Serial.print("TEST:SPEED=");',
        "  Serial.println(velocidad);",
        "  delay(200);",
        "}",
    ]
    return "\n".join(lines) + "\n"


def button_led_sketch(button_pin: int = 2, led_pin: int = 13) -> str:
    _validate_pin(button_pin)
    _validate_pin(led_pin)
    if button_pin == led_pin:
        raise ValueError(f"button_pin y led_pin deben ser distintos: {button_pin!r}")

    lines = [
        "void setup() {",
        f"  pinMode({button_pin}, INPUT_PULLUP);",
        f"  pinMode({led_pin}, OUTPUT);",
        "  Serial.begin(9600);",
        '  Serial.println("READY");',
        "}",
        "",
        "void loop() {",
        f"  int estado = digitalRead({button_pin});",
        "  if (estado == LOW) {",
        f"    digitalWrite({led_pin}, HIGH);",
        '    Serial.println("TEST:PRESSED");',
        "  } else {",
        f"    digitalWrite({led_pin}, LOW);",
        "  }",
        "  delay(50);",
        "}",
    ]
    return "\n".join(lines) + "\n"


def buzzer_button_sketch(button_pin: int = 2, buzzer_pin: int = 8) -> str:
    _validate_pin(button_pin)
    _validate_pin(buzzer_pin)
    if button_pin == buzzer_pin:
        raise ValueError(f"button_pin y buzzer_pin deben ser distintos: {button_pin!r}")

    lines = [
        "void setup() {",
        f"  pinMode({button_pin}, INPUT_PULLUP);",
        "  Serial.begin(9600);",
        '  Serial.println("READY");',
        "}",
        "",
        "void loop() {",
        f"  int estado = digitalRead({button_pin});",
        "  if (estado == LOW) {",
        f"    tone({buzzer_pin}, 880);",
        '    Serial.println("TEST:PRESSED");',
        "  } else {",
        f"    noTone({buzzer_pin});",
        '    Serial.println("TEST:SILENCIO");',
        "  }",
        "  delay(50);",
        "}",
    ]
    return "\n".join(lines) + "\n"


_LDR_THRESHOLD_MIN, _LDR_THRESHOLD_MAX = 0, 1023


def _validate_ldr_threshold(threshold: int) -> None:
    if (
        not isinstance(threshold, int)
        or isinstance(threshold, bool)
        or not _LDR_THRESHOLD_MIN <= threshold <= _LDR_THRESHOLD_MAX
    ):
        raise ValueError(
            f"threshold fuera de {_LDR_THRESHOLD_MIN}..{_LDR_THRESHOLD_MAX}: {threshold!r}"
        )


def _validate_analog_pin(name: str, pin: str) -> None:
    if pin not in _ANALOG_PINS:
        raise ValueError(f"{name} fuera de A0..A5: {pin!r}")


def ldr_led_sketch(ldr_pin: str = "A0", led_pin: int = 13, threshold: int = 300) -> str:
    _validate_analog_pin("ldr_pin", ldr_pin)
    _validate_pin(led_pin)
    _validate_ldr_threshold(threshold)

    lines = [
        "// Divisor: 5V -> LDR -> A0 -> resistencia 10k -> GND.",
        "// Mas luz = menos resistencia en el LDR = mas tension en A0 = lectura mas alta.",
        "// Logica de luz nocturna: a oscuras la lectura baja y el LED se enciende.",
        "void setup() {",
        f"  pinMode({led_pin}, OUTPUT);",
        "  Serial.begin(9600);",
        '  Serial.println("READY");',
        "}",
        "",
        "void loop() {",
        f"  int luz = analogRead({ldr_pin});",
        f"  if (luz < {threshold}) {{",
        f"    digitalWrite({led_pin}, HIGH);",
        '    Serial.println("TEST:LED=ON");',
        "  } else {",
        f"    digitalWrite({led_pin}, LOW);",
        '    Serial.println("TEST:LED=OFF");',
        "  }",
        '  Serial.print("TEST:LUZ=");',
        "  Serial.println(luz);",
        "  delay(200);",
        "}",
    ]
    return "\n".join(lines) + "\n"


# El default 130.0 cm sale de medir la escena real: la distancia simulada es
# ~112 cm segun los objetos, asi que con umbrales tipo 20 la barrera nunca abre
# y la demo no muestra nada. Con 130 arranca ABIERTO (servo 90 + LED verde).
def parking_servo_sketch(
    trig: int = 7,
    echo: int = 6,
    servo_pin: int = 9,
    red: int = 10,
    green: int = 11,
    blue: int = 3,
    threshold_cm: float = 130.0,
) -> str:
    pins = (trig, echo, servo_pin, red, green, blue)
    for pin in pins:
        _validate_pin(pin)
    if len(set(pins)) != len(pins):
        raise ValueError(
            "pines repetidos en barrera: "
            f"trig={trig}, echo={echo}, servo_pin={servo_pin}, red={red}, green={green}, blue={blue}"
        )
    _validate_threshold_cm(threshold_cm)
    threshold_text = _format_threshold(threshold_cm)

    lines = [
        "#include <Servo.h>",
        "",
        "Servo servo;",
        "",
        "void setup() {",
        f"  pinMode({trig}, OUTPUT);",
        f"  pinMode({echo}, INPUT);",
        f"  pinMode({red}, OUTPUT);",
        f"  pinMode({green}, OUTPUT);",
        f"  pinMode({blue}, OUTPUT);",
        f"  servo.attach({servo_pin});",
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
        "  int angulo;",
        f"  if (distancia < {threshold_text}) {{",
        "    angulo = 90;",
        f"    digitalWrite({green}, HIGH);",
        f"    digitalWrite({red}, LOW);",
        f"    digitalWrite({blue}, LOW);",
        '    Serial.println("TEST:ESTADO=ABIERTO");',
        "  } else {",
        "    angulo = 0;",
        f"    digitalWrite({red}, HIGH);",
        f"    digitalWrite({green}, LOW);",
        f"    digitalWrite({blue}, LOW);",
        '    Serial.println("TEST:ESTADO=CERRADO");',
        "  }",
        "  servo.write(angulo);",
        '  Serial.print("TEST:SERVO=");',
        "  Serial.println(angulo);",
        "  delay(200);",
        "}",
    ]
    return "\n".join(lines) + "\n"


_LCD_TITLE_MAX = 16
_LCD_PERIOD_MIN, _LCD_PERIOD_MAX = 100, 60000


def _validate_lcd_title(title: str) -> None:
    if not isinstance(title, str):
        raise ValueError(f"title debe ser str: {title!r}")
    if not title:
        raise ValueError("title no puede estar vacio")
    if len(title) > _LCD_TITLE_MAX:
        raise ValueError(f"title supera {_LCD_TITLE_MAX} caracteres: {title!r}")
    for bad in ('"', "\\", "\n", "\r"):
        if bad in title:
            raise ValueError(f"title no puede contener comillas dobles, barras invertidas ni saltos: {title!r}")


def _validate_lcd_period(period_ms: int) -> None:
    _validate_period_range("period_ms", period_ms, _LCD_PERIOD_MIN, _LCD_PERIOD_MAX)


def _validate_period_range(name: str, period_ms: int, low: int, high: int) -> None:
    if (
        not isinstance(period_ms, int)
        or isinstance(period_ms, bool)
        or not low <= period_ms <= high
    ):
        raise ValueError(f"{name} fuera de {low}..{high} ms: {period_ms!r}")


def lcd_counter_sketch(
    rs: int = 12,
    en: int = 11,
    d4: int = 5,
    d5: int = 4,
    d6: int = 3,
    d7: int = 2,
    title: str = "Tinkercad LCD",
    period_ms: int = 1000,
) -> str:
    pins = (rs, en, d4, d5, d6, d7)
    for pin in pins:
        _validate_pin(pin)
    if len(set(pins)) != len(pins):
        raise ValueError(
            "pines repetidos en LCD: "
            f"rs={rs}, en={en}, d4={d4}, d5={d5}, d6={d6}, d7={d7}"
        )
    _validate_lcd_title(title)
    _validate_lcd_period(period_ms)

    lines = [
        "// LCD 16x2 en modo 4 bits: RS, EN y D4..D7 al Arduino.",
        "// Contraste (VO) a GND en este montaje del simulador: con el potenciometro",
        "// en su posicion por defecto la pantalla queda en blanco.",
        "#include <LiquidCrystal.h>",
        "#include <stdio.h>",
        "",
        f"LiquidCrystal lcd({rs}, {en}, {d4}, {d5}, {d6}, {d7});",
        "",
        "unsigned long segundos = 0;",
        "",
        "void setup() {",
        "  Serial.begin(9600);",
        "  lcd.begin(16, 2);",
        "  lcd.clear();",
        "  lcd.setCursor(0, 0);",
        f'  lcd.print("{title}");',
        '  Serial.println("TEST:LCD=LISTO");',
        "}",
        "",
        "void loop() {",
        "  segundos = segundos + 1;",
        "  char linea[17];",
        '  snprintf(linea, sizeof(linea), "t=%lus", segundos);',
        "  for (int i = strlen(linea); i < 16; i++) {",
        "    linea[i] = ' ';",
        "  }",
        "  linea[16] = '\\0';",
        "  lcd.setCursor(0, 1);",
        "  lcd.print(linea);",
        '  Serial.print("TEST:SEG=");',
        "  Serial.println(segundos);",
        f"  delay({period_ms});",
        "}",
    ]
    return "\n".join(lines) + "\n"


_TEMP_PERIOD_MIN, _TEMP_PERIOD_MAX = 200, 60000


def lcd_temp_sketch(
    rs: int = 12,
    en: int = 11,
    d4: int = 5,
    d5: int = 4,
    d6: int = 3,
    d7: int = 2,
    sensor_pin: str = "A0",
    period_ms: int = 500,
) -> str:
    pins = (rs, en, d4, d5, d6, d7)
    for pin in pins:
        _validate_pin(pin)
    if len(set(pins)) != len(pins):
        raise ValueError(
            "pines repetidos en termometro LCD: "
            f"rs={rs}, en={en}, d4={d4}, d5={d5}, d6={d6}, d7={d7}"
        )
    _validate_analog_pin("sensor_pin", sensor_pin)
    _validate_period_range("period_ms", period_ms, _TEMP_PERIOD_MIN, _TEMP_PERIOD_MAX)

    lines = [
        "// Termometro TMP36 en LCD 16x2 (modo 4 bits): RS, EN y D4..D7 al Arduino.",
        "// Realidad del simulador: el TMP36 arranca en ~24.8 C y no cambia, asi que la",
        "// lectura es fija y la pantalla muestra siempre ese mismo valor.",
        "// Contraste (VO) a GND en este montaje: con el potenciometro en su posicion",
        "// por defecto la pantalla queda en blanco.",
        "#include <LiquidCrystal.h>",
        "#include <stdio.h>",
        "#include <stdlib.h>",
        "",
        f"LiquidCrystal lcd({rs}, {en}, {d4}, {d5}, {d6}, {d7});",
        "",
        "void setup() {",
        "  Serial.begin(9600);",
        "  lcd.begin(16, 2);",
        "  lcd.clear();",
        "  lcd.setCursor(0, 0);",
        '  lcd.print("Temperatura");',
        '  Serial.println("TEST:LCD=LISTO");',
        "}",
        "",
        "void loop() {",
        f"  int lectura = analogRead({sensor_pin});",
        "  float volts = lectura * 5.0/1023.0;",
        "  float temp = (volts - 0.5) * 100.0;",
        "  char temp_txt[8];",
        "  dtostrf(temp, 0, 2, temp_txt);",
        "  char linea[17];",
        '  snprintf(linea, sizeof(linea), "T=%s C", temp_txt);',
        "  for (int i = strlen(linea); i < 16; i++) {",
        "    linea[i] = ' ';",
        "  }",
        "  linea[16] = '\\0';",
        "  lcd.setCursor(0, 1);",
        "  lcd.print(linea);",
        '  Serial.print("TEST:TEMP=");',
        "  Serial.println(temp_txt);",
        f"  delay({period_ms});",
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
