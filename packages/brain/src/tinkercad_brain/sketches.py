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


# El default 130.0 cm sale de medir la escena real: el objeto del simulador queda a
# ~112 cm, asi que con umbrales tipo 20 la alarma nunca se enciende y la demo no
# muestra nada. Con 130 el circuito arranca con la alarma ENCENDIDA, observable.
def lcd_distance_sketch(
    trig: int = 7,
    echo: int = 6,
    buzzer: int = 8,
    rs: int = 12,
    en: int = 11,
    d4: int = 5,
    d5: int = 4,
    d6: int = 3,
    d7: int = 2,
    threshold_cm: float = 130.0,
    period_ms: int = 300,
) -> str:
    pins = (trig, echo, buzzer, rs, en, d4, d5, d6, d7)
    for pin in pins:
        _validate_pin(pin)
    if len(set(pins)) != len(pins):
        raise ValueError(
            "pines repetidos en medidor LCD: "
            f"trig={trig}, echo={echo}, buzzer={buzzer}, "
            f"rs={rs}, en={en}, d4={d4}, d5={d5}, d6={d6}, d7={d7}"
        )
    _validate_threshold_cm(threshold_cm)
    _validate_period_range("period_ms", period_ms, _LCD_PERIOD_MIN, _LCD_PERIOD_MAX)
    threshold_text = _format_threshold(threshold_cm)

    lines = [
        "// Medidor de distancia HC-SR04 en LCD 16x2 (modo 4 bits) con alarma sonora.",
        "// Contraste (VO) a GND en este montaje del simulador: con el potenciometro",
        "// en su posicion por defecto la pantalla queda en blanco.",
        "// Umbral por defecto 130 cm: la escena del simulador mide ~112 cm, asi el",
        "// circuito arranca en un estado observable (alarma encendida).",
        "#include <LiquidCrystal.h>",
        "#include <stdio.h>",
        "#include <stdlib.h>",
        "",
        f"LiquidCrystal lcd({rs}, {en}, {d4}, {d5}, {d6}, {d7});",
        "",
        "void setup() {",
        f"  pinMode({trig}, OUTPUT);",
        f"  pinMode({echo}, INPUT);",
        "  Serial.begin(9600);",
        "  lcd.begin(16, 2);",
        "  lcd.clear();",
        "  lcd.setCursor(0, 0);",
        '  lcd.print("Distancia");',
        '  Serial.println("TEST:LCD=LISTO");',
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
        "  char dist_txt[8];",
        "  dtostrf(distancia, 0, 1, dist_txt);",
        "  char linea[17];",
        '  snprintf(linea, sizeof(linea), "D=%s cm", dist_txt);',
        "  for (int i = strlen(linea); i < 16; i++) {",
        "    linea[i] = ' ';",
        "  }",
        "  linea[16] = '\\0';",
        "  lcd.setCursor(0, 1);",
        "  lcd.print(linea);",
        '  Serial.print("TEST:DIST=");',
        "  Serial.println(dist_txt);",
        f"  if (distancia < {threshold_text}) {{",
        f"    tone({buzzer}, 1000);",
        '    Serial.println("TEST:ALARMA=ON");',
        "  } else {",
        f"    noTone({buzzer});",
        '    Serial.println("TEST:ALARMA=OFF");',
        "  }",
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


# Patrones por digito, orden de segmentos a b c d e f g.
# 1 = segmento encendido (tabla logica, como en cualquier display de 7
# segmentos). El display de Tinkercad (did 129710) es de ANODO comun en el
# simulador: el comun va a 5V y el segmento enciende con LOW, asi que el
# sketch invierte cada bit al escribirlo.
SEVEN_SEG_DIGITS: tuple[tuple[int, ...], ...] = (
    (1, 1, 1, 1, 1, 1, 0),  # 0
    (0, 1, 1, 0, 0, 0, 0),  # 1
    (1, 1, 0, 1, 1, 0, 1),  # 2
    (1, 1, 1, 1, 0, 0, 1),  # 3
    (0, 1, 1, 0, 0, 1, 1),  # 4
    (1, 0, 1, 1, 0, 1, 1),  # 5
    (1, 0, 1, 1, 1, 1, 1),  # 6
    (1, 1, 1, 0, 0, 0, 0),  # 7
    (1, 1, 1, 1, 1, 1, 1),  # 8
    (1, 1, 1, 1, 0, 1, 1),  # 9
)


def seven_seg_sketch(
    a: int = 2,
    b: int = 3,
    c: int = 4,
    d: int = 5,
    e: int = 6,
    f: int = 7,
    g: int = 8,
    hold_ms: int = 400,
) -> str:
    """Contador 0-9 en un display 7 segmentos de anodo comun.

    El comun va a 5V y el segmento se enciende con LOW: la tabla
    ``SEVEN_SEG_DIGITS`` es logica (1 = encendido) y el sketch la invierte
    al escribir el pin. ``hold_ms`` por defecto 400 para que el ciclo
    completo (10 digitos) quepa en la ventana de simulacion del runner y
    el oraculo serial vea TEST:DIGITO=0..9.
    """
    pins = (a, b, c, d, e, f, g)
    for pin in pins:
        _validate_pin(pin)
    if len(set(pins)) != len(pins):
        raise ValueError(f"pines repetidos en 7 segmentos: {pins}")
    _validate_ms("hold_ms", hold_ms)

    rows = []
    for digit, pattern in enumerate(SEVEN_SEG_DIGITS):
        values = ", ".join(str(bit) for bit in pattern)
        rows.append(f"  {{{values}}},  // {digit}")
    table = "\n".join(rows)
    return "\n".join(
        [
            "// Contador 0-9 en display 7 segmentos de anodo comun (segmento en LOW).",
            "// Cada segmento pasa por su resistencia de 220 ohmios y el comun va a 5V.",
            f"const byte PINES[7] = {{{a}, {b}, {c}, {d}, {e}, {f}, {g}}};",
            "const byte DIGITOS[10][7] = {",
            table,
            "};",
            "",
            "void mostrar(byte digito) {",
            "  for (byte i = 0; i < 7; i++) {",
            "    digitalWrite(PINES[i], !DIGITOS[digito][i]);",
            "  }",
            "}",
            "",
            "void setup() {",
            "  for (byte i = 0; i < 7; i++) {",
            "    pinMode(PINES[i], OUTPUT);",
            "  }",
            "  Serial.begin(9600);",
            '  Serial.println("TEST:7SEG=LISTO");',
            "  mostrar(0);",
            "}",
            "",
            "void loop() {",
            "  for (byte digito = 0; digito < 10; digito++) {",
            "    mostrar(digito);",
            '    Serial.print("TEST:DIGITO=");',
            "    Serial.println(digito);",
            f"    delay({hold_ms});",
            "  }",
            "}",
            "",
        ]
    )


def _seven_seg_mask(pattern) -> int:
    """Byte de un digito con el bit i = segmento a+i encendido (logico)."""
    mask = 0
    for index, bit in enumerate(pattern):
        if bit:
            mask |= 1 << index
    return mask


def shift_register_sketch(
    ds: int = 11,
    shcp: int = 8,
    stcp: int = 12,
    hold_ms: int = 400,
) -> str:
    """Contador 0-9 con 74HC595 y display 7 segmentos de anodo comun.

    El 595 recibe los bits por ``shiftOut`` (DS = datos, SHCP = reloj) y los
    presenta en sus salidas con un pulso de STCP (latch). Q0..Q6 van a los
    segmentos a..g pasando por su resistencia, y el comun del display va a
    5V: como es anodo comun, el segmento enciende con el bit en 0, asi que
    la tabla se emite ya invertida. ``hold_ms`` por defecto 400 para que el
    ciclo completo quepa en la ventana de simulacion del runner.
    """
    pins = (ds, shcp, stcp)
    for pin in pins:
        _validate_pin(pin)
    if len(set(pins)) != len(pins):
        raise ValueError(f"pines repetidos en 74HC595: {pins}")
    _validate_ms("hold_ms", hold_ms)

    rows = []
    for digit, pattern in enumerate(SEVEN_SEG_DIGITS):
        mask = _seven_seg_mask(pattern)
        byte = (~mask) & 0x7F  # anodo comun: 0 enciende
        rows.append(f"  0x{byte:02X},  // {digit}")
    table = "\n".join(rows)
    return "\n".join(
        [
            "// Contador 0-9 con 74HC595 y display 7 segmentos de anodo comun.",
            "// DS = datos, SHCP = reloj, STCP = latch. Q0..Q6 -> a..g con su",
            "// resistencia; el comun del display va a 5V y el bit en 0 enciende.",
            f"const byte DS = {ds};",
            f"const byte SHCP = {shcp};",
            f"const byte STCP = {stcp};",
            "const byte DIGITOS[10] = {",
            table,
            "};",
            "",
            "void mostrar(byte digito) {",
            "  digitalWrite(STCP, LOW);",
            "  shiftOut(DS, SHCP, MSBFIRST, DIGITOS[digito]);",
            "  digitalWrite(STCP, HIGH);",
            "}",
            "",
            "void setup() {",
            "  pinMode(DS, OUTPUT);",
            "  pinMode(SHCP, OUTPUT);",
            "  pinMode(STCP, OUTPUT);",
            "  digitalWrite(STCP, HIGH);",
            "  Serial.begin(9600);",
            '  Serial.println("TEST:595=LISTO");',
            "  mostrar(0);",
            "}",
            "",
            "void loop() {",
            "  for (byte digito = 0; digito < 10; digito++) {",
            "    mostrar(digito);",
            '    Serial.print("TEST:DIGITO=");',
            "    Serial.println(digito);",
            f"    delay({hold_ms});",
            "  }",
            "}",
            "",
        ]
    )


def half_adder_sketch(
    a: int = 2,
    b: int = 3,
    sum_pin: int = 4,
    carry_pin: int = 5,
    settle_ms: int = 50,
) -> str:
    """Media suma con XOR (74HC86) y acarreo con dos NAND (74HC00).

    El Uno maneja A y B, y LEE la salida de las compuertas en ``sum_pin`` y
    ``carry_pin`` (esas salidas tambien encienden un LED con su resistencia).
    La tabla completa (a, b, suma, acarreo) sale por serial para que el
    oraculo del runner la compare con la verdad de una media suma.
    """
    pins = (a, b, sum_pin, carry_pin)
    for pin in pins:
        _validate_pin(pin)
    if len(set(pins)) != len(pins):
        raise ValueError(f"pines repetidos en media suma: {pins}")
    _validate_ms("settle_ms", settle_ms)

    return "\n".join(
        [
            "// Media suma: XOR (74HC86) da SUMA; NAND+NAND (74HC00) da ACARREO.",
            "// A y B los maneja el Uno; SUMA y ACARREO se leen como entradas.",
            f"const byte A = {a};",
            f"const byte B = {b};",
            f"const byte SUMA = {sum_pin};",
            f"const byte ACARREO = {carry_pin};",
            "",
            "void medir(byte a, byte b) {",
            "  digitalWrite(A, a);",
            "  digitalWrite(B, b);",
            f"  delay({settle_ms});",
            "  byte suma = digitalRead(SUMA);",
            "  byte acarreo = digitalRead(ACARREO);",
            '  Serial.print("TEST:HA=");',
            "  Serial.print(a);",
            '  Serial.print(",");',
            "  Serial.print(b);",
            '  Serial.print(",");',
            "  Serial.print(suma);",
            '  Serial.print(",");',
            "  Serial.println(acarreo);",
            "}",
            "",
            "void setup() {",
            "  pinMode(A, OUTPUT);",
            "  pinMode(B, OUTPUT);",
            "  pinMode(SUMA, INPUT);",
            "  pinMode(ACARREO, INPUT);",
            "  Serial.begin(9600);",
            '  Serial.println("TEST:LOGICA=LISTO");',
            "  medir(0, 0);",
            "  medir(0, 1);",
            "  medir(1, 0);",
            "  medir(1, 1);",
            "}",
            "",
            "void loop() {",
            "  delay(1000);",
            "}",
            "",
        ]
    )


def d_flip_flop_sketch(
    clk: int = 2,
    q: int = 4,
    settle_ms: int = 30,
    cycles: int = 8,
) -> str:
    """Biestable T con un 74HC74: 1D atado a 1NQ, reloj en 1CP.

    Cada flanco de subida del reloj debe invertir Q. El sketch no se cree
    el resultado: lee Q antes y despues de cada flanco, imprime la muestra
    (``TEST:FF=<q>``) y emite un veredicto explicito
    (``TEST:FF=TOGGLE-OK`` / ``TEST:FF=FAIL``) que el runner usa como
    oraculo. No importa el estado inicial: lo que se exige es que cada
    flanco cambie Q.
    """
    pins = (clk, q)
    for pin in pins:
        _validate_pin(pin)
    if clk == q:
        raise ValueError(f"pines repetidos en biestable D: {pins}")
    _validate_ms("settle_ms", settle_ms)
    if not isinstance(cycles, int) or isinstance(cycles, bool) or cycles < 1:
        raise ValueError(f"cycles debe ser un entero >= 1: {cycles!r}")

    return "\n".join(
        [
            "// Biestable T con 74HC74: 1D <- 1NQ y reloj en 1CP.",
            "// Cada flanco de subida debe invertir Q; el sketch lo verifica.",
            f"const byte CLK = {clk};",
            f"const byte Q = {q};",
            "",
            "void setup() {",
            "  pinMode(CLK, OUTPUT);",
            "  pinMode(Q, INPUT);",
            "  digitalWrite(CLK, LOW);",
            "  Serial.begin(9600);",
            "  delay(100);",
            '  Serial.println("TEST:FF=LISTO");',
            "  // Solo se comparan muestras consecutivas: leer Q antes del primer",
            "  // pulso no es fiable (el pin flota hasta que el biestable arranca).",
            "  int previo = -1;",
            "  bool alterna = true;",
            f"  for (byte i = 0; i < {cycles}; i++) {{",
            "    digitalWrite(CLK, HIGH);",
            f"    delay({settle_ms});",
            "    int actual = digitalRead(Q);",
            '    Serial.print("TEST:FF=");',
            "    Serial.println(actual);",
            "    if (previo >= 0 && actual == previo) {",
            "      alterna = false;",
            "    }",
            "    previo = actual;",
            "    digitalWrite(CLK, LOW);",
            f"    delay({settle_ms});",
            "  }",
            '  Serial.println(alterna ? "TEST:FF=TOGGLE-OK" : "TEST:FF=FAIL");',
            "}",
            "",
            "void loop() {",
            "  delay(1000);",
            "}",
            "",
        ]
    )


def astable_555_sketch(
    out_pin: int = 2,
    timeout_us: int = 500_000,
) -> str:
    """555 en astable: R=10k y C=10uF dan ~69 ms en alto (~14 Hz).

    El Uno no genera nada: solo mide. Engancha un pulso bajo completo para
    sincronizar, mide un pulso alto y otro bajo con ``pulseIn`` y emite la
    evidencia por serial (``TEST:555=ALTO``, ``BAJO`` y ``FREQ``) mas un
    veredicto explicito que el runner usa como oraculo. Los timeouts acotan
    el peor caso (555 que no oscila) para no comerse la ventana de 5 s.
    """
    _validate_pin(out_pin)
    if not isinstance(timeout_us, int) or isinstance(timeout_us, bool) or timeout_us < 1000:
        raise ValueError(f"timeout_us debe ser un entero >= 1000: {timeout_us!r}")

    return "\n".join(
        [
            "// 555 astable (R=10k, C=10uF): pulso alto ~69 ms (~14 Hz).",
            "// El Uno solo mide; el oraculo es el serial, no el pixel.",
            f"const byte OUT = {out_pin};",
            f"const unsigned long TIMEOUT = {timeout_us}UL;",
            "",
            "void setup() {",
            "  pinMode(OUT, INPUT);",
            "  Serial.begin(9600);",
            "  delay(100);",
            '  Serial.println("TEST:555=LISTO");',
            "  // Sincroniza con un pulso bajo completo para medir uno entero.",
            "  pulseIn(OUT, LOW, TIMEOUT);",
            "  unsigned long alto = pulseIn(OUT, HIGH, TIMEOUT);",
            "  unsigned long bajo = pulseIn(OUT, LOW, TIMEOUT);",
            "  unsigned long periodo = alto + bajo;",
            '  Serial.print("TEST:555=ALTO,");',
            "  Serial.println(alto);",
            '  Serial.print("TEST:555=BAJO,");',
            "  Serial.println(bajo);",
            "  if (periodo > 0) {",
            '    Serial.print("TEST:555=FREQ,");',
            "    Serial.println(1000000.0 / periodo, 1);",
            "  } else {",
            '    Serial.println("TEST:555=FREQ,0.0");',
            "  }",
            "  bool ok = alto >= 40000UL && alto <= 200000UL",
            "            && periodo >= 40000UL && periodo <= 400000UL;",
            '  Serial.println(ok ? "TEST:555=OK" : "TEST:555=FAIL");',
            "}",
            "",
            "void loop() {",
            "  delay(1000);",
            "}",
            "",
        ]
    )


def binary_counter_sketch(
    clk: int = 2,
    reset: int = 3,
    bits: tuple[int, int, int, int] = (4, 5, 6, 7),
    settle_ms: int = 20,
    pulses: int = 16,
) -> str:
    """Contador binario 74HC93: Q0 -> CP1 (ripple) y reloj del Uno en CP0.

    El sketch resetea el contador (MR1/MR2 activos en alto) y luego da
    ``pulses`` flancos de bajada en CP0. Tras cada flanco lee el nibble
    Q0..Q3 y lo imprime en decimal (``TEST:CONTADOR=<n>``), asi el oraculo
    comprueba la secuencia completa y no un solo valor.
    """
    for pin in (clk, reset) + tuple(bits):
        _validate_pin(pin)
    if len(set((clk, reset) + tuple(bits))) != 6:
        raise ValueError(f"pines repetidos en contador: {(clk, reset) + tuple(bits)}")
    _validate_ms("settle_ms", settle_ms)
    if not isinstance(pulses, int) or isinstance(pulses, bool) or not 1 <= pulses <= 64:
        raise ValueError(f"pulses debe ser un entero 1..64: {pulses!r}")

    q0, q1, q2, q3 = bits
    return "\n".join(
        [
            "// Contador binario 74HC93: Q0 -> CP1 (ripple), reloj en CP0,",
            "// MR1/MR2 al pin de reset. Cuenta en el flanco de bajada.",
            f"const byte CLK = {clk};",
            f"const byte RST = {reset};",
            f"const byte Q0 = {q0};",
            f"const byte Q1 = {q1};",
            f"const byte Q2 = {q2};",
            f"const byte Q3 = {q3};",
            "",
            "byte leer() {",
            "  byte valor = 0;",
            "  if (digitalRead(Q0)) valor |= 1;",
            "  if (digitalRead(Q1)) valor |= 2;",
            "  if (digitalRead(Q2)) valor |= 4;",
            "  if (digitalRead(Q3)) valor |= 8;",
            "  return valor;",
            "}",
            "",
            "void pulso() {",
            "  digitalWrite(CLK, HIGH);",
            f"  delay({settle_ms});",
            "  digitalWrite(CLK, LOW);",
            f"  delay({settle_ms});",
            "}",
            "",
            "void setup() {",
            "  pinMode(CLK, OUTPUT);",
            "  pinMode(RST, OUTPUT);",
            "  pinMode(Q0, INPUT);",
            "  pinMode(Q1, INPUT);",
            "  pinMode(Q2, INPUT);",
            "  pinMode(Q3, INPUT);",
            "  digitalWrite(CLK, LOW);",
            "  digitalWrite(RST, LOW);",
            "  Serial.begin(9600);",
            "  delay(50);",
            "  // Reseteo explicito: MR1 y MR2 son activos en alto.",
            "  digitalWrite(RST, HIGH);",
            f"  delay({settle_ms});",
            "  digitalWrite(RST, LOW);",
            f"  delay({settle_ms});",
            '  Serial.println("TEST:CONTADOR=LISTO");',
            f"  for (byte i = 0; i < {pulses}; i++) {{",
            "    pulso();",
            '    Serial.print("TEST:CONTADOR=");',
            "    Serial.println(leer());",
            "  }",
            '  Serial.println("TEST:CONTADOR=FIN");',
            "}",
            "",
            "void loop() {",
            "  // Demostracion visual: el contador sigue avanzando despacio,",
            "  // sin serial, para que los LEDs se vean contar en binario.",
            "  digitalWrite(CLK, HIGH);",
            "  delay(600);",
            "  digitalWrite(CLK, LOW);",
            "  delay(600);",
            "}",
            "",
        ]
    )


def decade_counter_sketch(
    clk: int = 2,
    bits: tuple[int, int, int, int] = (4, 5, 6, 7),
    step_ms: int = 400,
    cycles: int = 8,
) -> str:
    """Carrusel de 4 salidas con el 74HC4017 (contador Johnson).

    El 4017 avanza en cada flanco de subida de CP0 y tiene las salidas
    one-hot. Q4 se cablea a MR (reset), asi que el carrusel da la vuelta en
    cuatro pasos sin intervencion del Uno. El sketch solo da el reloj, lee
    que salida esta activa y la imprime; los LEDs muestran lo mismo.

    ``step_ms`` es 400 y no 500: con 8 pasos de medio segundo el ciclo
    completo son 4 s y el ``FIN`` cae fuera de la ventana de 5 s del runner
    (la misma leccion de la fase 28). A 400 ms el oraculo cierra en 3.3 s.
    """
    for pin in (clk,) + tuple(bits):
        _validate_pin(pin)
    if len(set((clk,) + tuple(bits))) != 5:
        raise ValueError(f"pines repetidos en carrusel: {(clk,) + tuple(bits)}")
    _validate_ms("step_ms", step_ms)
    if not isinstance(cycles, int) or isinstance(cycles, bool) or not 1 <= cycles <= 20:
        raise ValueError(f"cycles debe ser un entero 1..20: {cycles!r}")
    if step_ms < 30:
        raise ValueError(f"step_ms debe ser >= 30: {step_ms!r}")

    q0, q1, q2, q3 = bits
    return "\n".join(
        [
            "// 74HC4017: Q4 -> MR para que el carrusel vuelva a Q0 en 4 pasos.",
            "// El Uno da el reloj en CP0 y lee la salida activa.",
            f"const byte CLK = {clk};",
            f"const byte Q0 = {q0};",
            f"const byte Q1 = {q1};",
            f"const byte Q2 = {q2};",
            f"const byte Q3 = {q3};",
            "",
            "byte leer() {",
            "  if (digitalRead(Q0)) return 0;",
            "  if (digitalRead(Q1)) return 1;",
            "  if (digitalRead(Q2)) return 2;",
            "  if (digitalRead(Q3)) return 3;",
            "  return 9;",
            "}",
            "",
            "void setup() {",
            "  pinMode(CLK, OUTPUT);",
            "  pinMode(Q0, INPUT);",
            "  pinMode(Q1, INPUT);",
            "  pinMode(Q2, INPUT);",
            "  pinMode(Q3, INPUT);",
            "  digitalWrite(CLK, LOW);",
            "  Serial.begin(9600);",
            "  delay(100);",
            '  Serial.println("TEST:4017=LISTO");',
            "}",
            "",
            "void loop() {",
            f"  for (byte i = 0; i < {cycles}; i++) {{",
            "    digitalWrite(CLK, HIGH);",
            "    delay(20);",
            '    Serial.print("TEST:4017=");',
            "    Serial.println(leer());",
            "    digitalWrite(CLK, LOW);",
            f"    delay({step_ms - 20});",
            "  }",
            '  Serial.println("TEST:4017=FIN");',
            "  while (true) { delay(1000); }",
            "}",
            "",
        ]
    )


def faro_ldr_relay_sketch(
    ldr_pin: str = "A0",
    coil_pin: int = 2,
    sense_pin: str = "A1",
    threshold: int = 300,
    step_ms: int = 300,
    cycles: int = 4,
) -> str:
    """Faro automatico: LDR decide, rele SPDT conmuta la bombilla.

    El LDR va en divisor (5V -> LDR -> A0 -> R -> GND), asi que a oscuras la
    lectura baja. El Uno no puede mover la bobina del rele: la maneja con un
    NPN (base por resistencia 1k, emisor a GND, colector a COIL2) y un diodo
    de recirculacion entre COIL1 y COIL2. El contacto COM1-R1 es el normal
    abierto: al energizar la bobina cierra y alimenta la bombilla.

    ``A1`` se cablea al nodo del contacto para tener oraculo: si el contacto
    cierra, A1 ve 5 V; si abre, la bombilla lo baja a GND. Al final se apaga
    la bobina y se vuelve a leer, de modo que el serial demuestra las dos
    posiciones del contacto y no solo la de encendido.
    """
    _validate_analog_pin("ldr_pin", ldr_pin)
    _validate_analog_pin("sense_pin", sense_pin)
    _validate_pin(coil_pin)
    _validate_ldr_threshold(threshold)
    _validate_ms("step_ms", step_ms)
    if sense_pin == ldr_pin:
        raise ValueError(f"sense_pin y ldr_pin no pueden ser el mismo: {ldr_pin!r}")
    if not isinstance(cycles, int) or isinstance(cycles, bool) or not 1 <= cycles <= 10:
        raise ValueError(f"cycles debe ser un entero 1..10: {cycles!r}")
    if step_ms < 30:
        raise ValueError(f"step_ms debe ser >= 30: {step_ms!r}")

    return "\n".join(
        [
            "// Faro: LDR en divisor -> A0. Rele por NPN desde D2 (base 1k).",
            "// COM1-R1 es el contacto NA; A1 lee el nodo para confirmarlo.",
            f"const byte COIL = {coil_pin};",
            "",
            "byte foco() {",
            f"  return analogRead({sense_pin}) > 700 ? 1 : 0;",
            "}",
            "",
            "void setup() {",
            "  pinMode(COIL, OUTPUT);",
            "  digitalWrite(COIL, LOW);",
            "  Serial.begin(9600);",
            "  delay(100);",
            '  Serial.println("TEST:FARO=LISTO");',
            "}",
            "",
            "void loop() {",
            f"  for (byte i = 0; i < {cycles}; i++) {{",
            f"    int luz = analogRead({ldr_pin});",
            f"    if (luz < {threshold}) digitalWrite(COIL, HIGH);",
            "    else digitalWrite(COIL, LOW);",
            f"    delay({step_ms});",
            '    Serial.print("TEST:LUZ=");',
            "    Serial.println(luz);",
            '    Serial.print("TEST:RELE=");',
            "    Serial.println(digitalRead(COIL) ? \"ON\" : \"OFF\");",
            '    Serial.print("TEST:FOCO=");',
            "    Serial.println(foco());",
            "  }",
            "  digitalWrite(COIL, LOW);",
            f"  delay({step_ms});",
            '  Serial.println("TEST:RELE=OFF");',
            '  Serial.print("TEST:FOCO=");',
            "  Serial.println(foco());",
            '  Serial.println("TEST:FARO=FIN");',
            "  while (true) { delay(1000); }",
            "}",
            "",
        ]
    )


def pir_alarm_sketch(
    pir_pin: int = 2,
    buzzer_pin: int = 3,
    led_pin: int = 4,
    tone_hz: int = 1000,
    poll_ms: int = 100,
) -> str:
    """Alarma de movimiento: PIR en D2, buzzer en D3 y LED en D4.

    El PIR entrega un nivel (alto con movimiento). El sketch no imprime en
    cada vuelta: solo cuando el estado **cambia**, ademas del estado inicial.
    Asi el oraculo es legible (``TEST:MOV=1`` / ``TEST:MOV=0``) y la ventana
    de 5 s del runner no se llena de ceros. El estimulo (mover algo frente al
    sensor) lo da el simulador, no el sketch.
    """
    _validate_pin(pir_pin)
    _validate_pin(buzzer_pin)
    _validate_pin(led_pin)
    if len({pir_pin, buzzer_pin, led_pin}) != 3:
        raise ValueError(
            f"los tres pines deben ser distintos: {pir_pin}, {buzzer_pin}, {led_pin}"
        )
    if not isinstance(tone_hz, int) or isinstance(tone_hz, bool) or not 100 <= tone_hz <= 5000:
        raise ValueError(f"tone_hz debe ser un entero 100..5000: {tone_hz!r}")
    _validate_ms("poll_ms", poll_ms)
    if poll_ms < 20:
        raise ValueError(f"poll_ms debe ser >= 20: {poll_ms!r}")

    return "\n".join(
        [
            "// Alarma: PIR en D2, buzzer en D3 y LED en D4.",
            "// Imprime solo los cambios de estado, no cada vuelta.",
            f"const byte PIR = {pir_pin};",
            f"const byte BUZZER = {buzzer_pin};",
            f"const byte LED = {led_pin};",
            "byte estado = 0;",
            "",
            "void avisar(byte movimiento) {",
            "  digitalWrite(LED, movimiento ? HIGH : LOW);",
            f"  if (movimiento) tone(BUZZER, {tone_hz});",
            "  else noTone(BUZZER);",
            "}",
            "",
            "void setup() {",
            "  pinMode(PIR, INPUT);",
            "  pinMode(BUZZER, OUTPUT);",
            "  pinMode(LED, OUTPUT);",
            "  Serial.begin(9600);",
            "  delay(100);",
            '  Serial.println("TEST:PIR=LISTO");',
            "  estado = digitalRead(PIR) ? 1 : 0;",
            "  avisar(estado);",
            '  Serial.print("TEST:MOV=");',
            "  Serial.println(estado);",
            "}",
            "",
            "void loop() {",
            "  byte movimiento = digitalRead(PIR) ? 1 : 0;",
            "  if (movimiento != estado) {",
            "    estado = movimiento;",
            "    avisar(movimiento);",
            '    Serial.print("TEST:MOV=");',
            "    Serial.println(movimiento);",
            "  }",
            f"  delay({poll_ms});",
            "}",
            "",
        ]
    )


_KEYPAD_LABELS = (
    "123A",
    "456B",
    "789C",
    "*0#D",
)


def keypad_lock_sketch(
    row_pins: tuple[int, ...] = (2, 3, 4, 5),
    column_pins: tuple[int, ...] = (6, 7, 8, 9),
    code: str = "1234",
    open_led: int = 10,
    deny_led: int = 11,
    debounce_ms: int = 20,
) -> str:
    """Cerradura con teclado 4x4: clave de 4 teclas y dos LEDs.

    El teclado se barre sin libreria: una fila en LOW, las columnas con
    ``INPUT_PULLUP``. La tecla queda pulsada hasta que se lee, asi que el
    sketch **espera a que se suelte** antes de devolver el caracter: una
    pulsacion mantenida vale una sola tecla, no una rafaga.

    El oraculo imprime ``TEST:TECLA=<tecla>`` por cada pulsacion aceptada y,
    al completar cuatro, ``TEST:CLAVE=OK`` o ``TEST:CLAVE=FALLA``. El LED de
    apertura (``open_led``) queda encendido con la clave correcta y el de
    rechazo (``deny_led``) con la incorrecta, hasta el siguiente intento.
    """
    if len(row_pins) != 4 or len(column_pins) != 4:
        raise ValueError("el teclado 4x4 necesita 4 filas y 4 columnas")
    for pin in (*row_pins, *column_pins):
        _validate_pin(pin)
    if len(set((*row_pins, *column_pins))) != 8:
        raise ValueError(f"los ocho pines deben ser distintos: {row_pins}, {column_pins}")
    _validate_pin(open_led)
    _validate_pin(deny_led)
    if open_led == deny_led or {open_led, deny_led} & set((*row_pins, *column_pins)):
        raise ValueError(f"los LEDs no pueden repetir pines del teclado: {open_led}, {deny_led}")
    if not isinstance(code, str) or len(code) != 4:
        raise ValueError(f"code debe ser una cadena de 4 teclas: {code!r}")
    validas = set("".join(_KEYPAD_LABELS))
    if any(key not in validas for key in code):
        raise ValueError(f"code solo admite teclas del teclado 4x4: {code!r}")
    _validate_ms("debounce_ms", debounce_ms)
    if not 5 <= debounce_ms <= 200:
        raise ValueError(f"debounce_ms debe estar en 5..200: {debounce_ms!r}")

    filas = ", ".join(str(pin) for pin in row_pins)
    columnas = ", ".join(str(pin) for pin in column_pins)
    tabla = ",\n  ".join(
        "{" + ", ".join(f"'{key}'" for key in fila) + "}" for fila in _KEYPAD_LABELS
    )
    clave = ", ".join(f"'{key}'" for key in code)
    return "\n".join(
        [
            "// Cerradura: teclado 4x4, clave y dos LEDs de respuesta.",
            f"// Clave: {code}. Apertura en D{open_led}, rechazo en D{deny_led}.",
            f"const byte FILAS[4] = {{{filas}}};",
            f"const byte COLS[4] = {{{columnas}}};",
            "const char TECLAS[4][4] = {",
            f"  {tabla}",
            "};",
            f"const char CLAVE[4] = {{{clave}}};",
            f"const byte LED_OK = {open_led};",
            f"const byte LED_FALLA = {deny_led};",
            "byte digitos = 0;",
            "byte aciertos = 0;",
            "",
            "char leerTecla() {",
            "  for (byte f = 0; f < 4; f++) {",
            "    digitalWrite(FILAS[f], LOW);",
            "    delay(2);",
            "    for (byte c = 0; c < 4; c++) {",
            "      if (digitalRead(COLS[c]) == LOW) {",
            f"        delay({debounce_ms});",
            "        if (digitalRead(COLS[c]) == LOW) {",
            "          // Una pulsacion mantenida vale una sola tecla.",
            "          while (digitalRead(COLS[c]) == LOW) delay(5);",
            "          digitalWrite(FILAS[f], HIGH);",
            "          return TECLAS[f][c];",
            "        }",
            "      }",
            "    }",
            "    digitalWrite(FILAS[f], HIGH);",
            "  }",
            "  return 0;",
            "}",
            "",
            "void setup() {",
            "  Serial.begin(9600);",
            "  for (byte i = 0; i < 4; i++) {",
            "    pinMode(FILAS[i], OUTPUT);",
            "    digitalWrite(FILAS[i], HIGH);",
            "    pinMode(COLS[i], INPUT_PULLUP);",
            "  }",
            "  pinMode(LED_OK, OUTPUT);",
            "  pinMode(LED_FALLA, OUTPUT);",
            "  digitalWrite(LED_OK, LOW);",
            "  digitalWrite(LED_FALLA, LOW);",
            '  Serial.println("TEST:KP=LISTO");',
            '  Serial.println("TEST:CLAVE=ESPERANDO");',
            "}",
            "",
            "void loop() {",
            "  char tecla = leerTecla();",
            "  if (tecla == 0) return;",
            '  Serial.print("TEST:TECLA=");',
            "  Serial.println(tecla);",
            "  if (digitos < 4) {",
            "    if (tecla == CLAVE[digitos]) aciertos++;",
            "    digitos++;",
            "  }",
            "  if (digitos == 4) {",
            "    bool abierta = (aciertos == 4);",
            "    digitalWrite(LED_OK, abierta ? HIGH : LOW);",
            "    digitalWrite(LED_FALLA, abierta ? LOW : HIGH);",
            '    Serial.print("TEST:CLAVE=");',
            '    Serial.println(abierta ? "OK" : "FALLA");',
            "    digitos = 0;",
            "    aciertos = 0;",
            "  }",
            "}",
            "",
        ]
    )


def keypad_lcd_sketch(
    row_pins: tuple[int, ...] = (2, 3, 4, 5),
    column_pins: tuple[int, ...] = (6, 7, 8, 9),
    lcd_pins: tuple[str, ...] = ("A0", "A1", "A2", "A3", "A4", "A5"),
    code: str = "1234",
    debounce_ms: int = 20,
    hold_ms: int = 1500,
) -> str:
    """Caja fuerte: teclado 4x4 y LCD 16x2 en modo 4 bits.

    Primer circuito que integra dos bloques ya verificados por separado:
    entrada matricial (teclado) y salida de texto (LCD). El teclado ocupa
    D2..D9 y el LCD los analogicos A0..A5, que funcionan como digitales
    (verificado en vivo): sin repartir los pines no caben los dos.

    El LCD muestra la clave enmascarada y el resultado; el oraculo imprime
    ``TEST:TECLA=<tecla>`` por pulsacion aceptada, ``TEST:CLAVE=OK`` o
    ``FALLA`` al completar cuatro, y ``TEST:PANTALLA=<texto>`` con lo que
    quedo escrito en la segunda linea.
    """
    if len(row_pins) != 4 or len(column_pins) != 4:
        raise ValueError("el teclado 4x4 necesita 4 filas y 4 columnas")
    for pin in (*row_pins, *column_pins):
        _validate_pin(pin)
    if len(set((*row_pins, *column_pins))) != 8:
        raise ValueError(f"los ocho pines del teclado deben ser distintos: {row_pins}, {column_pins}")
    if len(lcd_pins) != 6:
        raise ValueError(f"el LCD en 4 bits necesita 6 pines: {lcd_pins!r}")
    for pin in lcd_pins:
        if pin not in _ANALOG_PINS:
            raise ValueError(f"lcd_pins debe ser A0..A5: {lcd_pins!r}")
    if len(set(lcd_pins)) != 6:
        raise ValueError(f"lcd_pins repetidos: {lcd_pins!r}")
    if not isinstance(code, str) or len(code) != 4:
        raise ValueError(f"code debe ser una cadena de 4 teclas: {code!r}")
    validas = set("".join(_KEYPAD_LABELS))
    if any(key not in validas for key in code):
        raise ValueError(f"code solo admite teclas del teclado 4x4: {code!r}")
    _validate_ms("debounce_ms", debounce_ms)
    if not 5 <= debounce_ms <= 200:
        raise ValueError(f"debounce_ms debe estar en 5..200: {debounce_ms!r}")
    _validate_ms("hold_ms", hold_ms)
    if not 200 <= hold_ms <= 5000:
        raise ValueError(f"hold_ms debe estar en 200..5000: {hold_ms!r}")

    filas = ", ".join(str(pin) for pin in row_pins)
    columnas = ", ".join(str(pin) for pin in column_pins)
    tabla = ",\n  ".join(
        "{" + ", ".join(f"'{key}'" for key in fila) + "}" for fila in _KEYPAD_LABELS
    )
    clave = ", ".join(f"'{key}'" for key in code)
    lcd = ", ".join(lcd_pins)
    return "\n".join(
        [
            "// Caja fuerte: teclado 4x4 a D2..D9 y LCD 16x2 en 4 bits a A0..A5.",
            f"// Clave: {code}.",
            "#include <LiquidCrystal.h>",
            "",
            f"const byte FILAS[4] = {{{filas}}};",
            f"const byte COLS[4] = {{{columnas}}};",
            "const char TECLAS[4][4] = {",
            f"  {tabla}",
            "};",
            f"const char CLAVE[4] = {{{clave}}};",
            "",
            f"LiquidCrystal lcd({lcd});",
            "byte digitos = 0;",
            "byte aciertos = 0;",
            "",
            "char leerTecla() {",
            "  for (byte f = 0; f < 4; f++) {",
            "    digitalWrite(FILAS[f], LOW);",
            "    delay(2);",
            "    for (byte c = 0; c < 4; c++) {",
            "      if (digitalRead(COLS[c]) == LOW) {",
            f"        delay({debounce_ms});",
            "        if (digitalRead(COLS[c]) == LOW) {",
            "          // Una pulsacion mantenida vale una sola tecla.",
            "          while (digitalRead(COLS[c]) == LOW) delay(5);",
            "          digitalWrite(FILAS[f], HIGH);",
            "          return TECLAS[f][c];",
            "        }",
            "      }",
            "    }",
            "    digitalWrite(FILAS[f], HIGH);",
            "  }",
            "  return 0;",
            "}",
            "",
            "void linea(byte fila, const char* texto) {",
            "  lcd.setCursor(0, fila);",
            "  lcd.print(texto);",
            "  byte largo = 0;",
            "  while (texto[largo] != 0) largo++;",
            "  // Rellena hasta 16 para borrar los restos del texto anterior.",
            "  for (byte i = largo; i < 16; i++) lcd.print(' ');",
            "}",
            "",
            "void setup() {",
            "  Serial.begin(9600);",
            "  for (byte i = 0; i < 4; i++) {",
            "    pinMode(FILAS[i], OUTPUT);",
            "    digitalWrite(FILAS[i], HIGH);",
            "    pinMode(COLS[i], INPUT_PULLUP);",
            "  }",
            "  lcd.begin(16, 2);",
            '  linea(0, "Clave:");',
            '  linea(1, "");',
            '  Serial.println("TEST:KP=LISTO");',
            '  Serial.println("TEST:CLAVE=ESPERANDO");',
            "}",
            "",
            "void loop() {",
            "  char tecla = leerTecla();",
            "  if (tecla == 0) return;",
            '  Serial.print("TEST:TECLA=");',
            "  Serial.println(tecla);",
            "  if (digitos < 4) {",
            "    if (tecla == CLAVE[digitos]) aciertos++;",
            "    digitos++;",
            "    lcd.setCursor(digitos - 1, 1);",
            "    lcd.print('*');",
            "  }",
            "  if (digitos == 4) {",
            "    bool abierta = (aciertos == 4);",
            '    linea(1, abierta ? "ABIERTO" : "DENEGADO");',
            '    Serial.print("TEST:CLAVE=");',
            '    Serial.println(abierta ? "OK" : "FALLA");',
            '    Serial.print("TEST:PANTALLA=");',
            '    Serial.println(abierta ? "ABIERTO" : "DENEGADO");',
            f"    delay({hold_ms});",
            '    linea(1, "");',
            '    linea(0, "Clave:");',
            "    digitos = 0;",
            "    aciertos = 0;",
            "  }",
            "}",
            "",
        ]
    )


def access_control_sketch(
    row_pins: tuple[int, ...] = (2, 3, 4, 5),
    column_pins: tuple[int, ...] = (6, 7, 8, 9),
    lcd_pins: tuple[str, ...] = ("A0", "A1", "A2", "A3", "A4", "A5"),
    servo_pin: int = 10,
    code: str = "1234",
    open_angle: int = 90,
    closed_angle: int = 0,
    debounce_ms: int = 20,
    hold_ms: int = 1500,
) -> str:
    """Control de acceso: teclado 4x4, LCD 16x2 y servo como cerrojo.

    Primer circuito que integra tres bloques verificados por separado:
    entrada matricial (teclado), salida de texto (LCD) y actuador (servo).
    El teclado ocupa D2..D9 y el LCD los analogicos A0..A5, que funcionan
    como digitales (verificado en vivo); el servo va libre a la derecha de
    la placa (``"free_parts"``) porque montado en ella su cuerpo tapa los
    taps del riel y su senal rodea el Uno.

    El oraculo imprime ``TEST:TECLA=<tecla>`` por pulsacion aceptada,
    ``TEST:CLAVE=OK``/``FALLA`` al completar cuatro, ``TEST:SERVO=<angulo>``
    con la posicion del cerrojo y ``TEST:PANTALLA=<texto>`` con lo que
    quedo escrito en la segunda linea del display.
    """
    if len(row_pins) != 4 or len(column_pins) != 4:
        raise ValueError("el teclado 4x4 necesita 4 filas y 4 columnas")
    for pin in (*row_pins, *column_pins):
        _validate_pin(pin)
    if len(set((*row_pins, *column_pins))) != 8:
        raise ValueError(f"los ocho pines del teclado deben ser distintos: {row_pins}, {column_pins}")
    if len(lcd_pins) != 6:
        raise ValueError(f"el LCD en 4 bits necesita 6 pines: {lcd_pins!r}")
    for pin in lcd_pins:
        if pin not in _ANALOG_PINS:
            raise ValueError(f"lcd_pins debe ser A0..A5: {lcd_pins!r}")
    if len(set(lcd_pins)) != 6:
        raise ValueError(f"lcd_pins repetidos: {lcd_pins!r}")
    _validate_pin(servo_pin)
    if servo_pin in (*row_pins, *column_pins):
        raise ValueError(f"servo_pin repite un pin del teclado: {servo_pin!r}")
    if not isinstance(code, str) or len(code) != 4:
        raise ValueError(f"code debe ser una cadena de 4 teclas: {code!r}")
    validas = set("".join(_KEYPAD_LABELS))
    if any(key not in validas for key in code):
        raise ValueError(f"code solo admite teclas del teclado 4x4: {code!r}")
    for name, angle in (("open_angle", open_angle), ("closed_angle", closed_angle)):
        if not isinstance(angle, int) or isinstance(angle, bool) or not 0 <= angle <= 180:
            raise ValueError(f"{name} debe ser un entero 0..180: {angle!r}")
    if open_angle == closed_angle:
        raise ValueError(f"open_angle y closed_angle deben diferir: {open_angle!r}")
    _validate_ms("debounce_ms", debounce_ms)
    if not 5 <= debounce_ms <= 200:
        raise ValueError(f"debounce_ms debe estar en 5..200: {debounce_ms!r}")
    _validate_ms("hold_ms", hold_ms)
    if not 200 <= hold_ms <= 5000:
        raise ValueError(f"hold_ms debe estar en 200..5000: {hold_ms!r}")

    filas = ", ".join(str(pin) for pin in row_pins)
    columnas = ", ".join(str(pin) for pin in column_pins)
    tabla = ",\n  ".join(
        "{" + ", ".join(f"'{key}'" for key in fila) + "}" for fila in _KEYPAD_LABELS
    )
    clave = ", ".join(f"'{key}'" for key in code)
    lcd = ", ".join(lcd_pins)
    return "\n".join(
        [
            "// Control de acceso: teclado 4x4, LCD 16x2 y servo como cerrojo.",
            f"// Clave: {code}. Abierto en {open_angle} grados, cerrado en {closed_angle}.",
            "#include <LiquidCrystal.h>",
            "#include <Servo.h>",
            "",
            f"const byte FILAS[4] = {{{filas}}};",
            f"const byte COLS[4] = {{{columnas}}};",
            "const char TECLAS[4][4] = {",
            f"  {tabla}",
            "};",
            f"const char CLAVE[4] = {{{clave}}};",
            f"const byte PIN_SERVO = {servo_pin};",
            f"const byte ABIERTO = {open_angle};",
            f"const byte CERRADO = {closed_angle};",
            "",
            f"LiquidCrystal lcd({lcd});",
            "Servo cerrojo;",
            "byte digitos = 0;",
            "byte aciertos = 0;",
            "",
            "char leerTecla() {",
            "  for (byte f = 0; f < 4; f++) {",
            "    digitalWrite(FILAS[f], LOW);",
            "    delay(2);",
            "    for (byte c = 0; c < 4; c++) {",
            "      if (digitalRead(COLS[c]) == LOW) {",
            f"        delay({debounce_ms});",
            "        if (digitalRead(COLS[c]) == LOW) {",
            "          // Una pulsacion mantenida vale una sola tecla.",
            "          while (digitalRead(COLS[c]) == LOW) delay(5);",
            "          digitalWrite(FILAS[f], HIGH);",
            "          return TECLAS[f][c];",
            "        }",
            "      }",
            "    }",
            "    digitalWrite(FILAS[f], HIGH);",
            "  }",
            "  return 0;",
            "}",
            "",
            "void linea(byte fila, const char* texto) {",
            "  lcd.setCursor(0, fila);",
            "  lcd.print(texto);",
            "  byte largo = 0;",
            "  while (texto[largo] != 0) largo++;",
            "  // Rellena hasta 16 para borrar los restos del texto anterior.",
            "  for (byte i = largo; i < 16; i++) lcd.print(' ');",
            "}",
            "",
            "void setup() {",
            "  Serial.begin(9600);",
            "  for (byte i = 0; i < 4; i++) {",
            "    pinMode(FILAS[i], OUTPUT);",
            "    digitalWrite(FILAS[i], HIGH);",
            "    pinMode(COLS[i], INPUT_PULLUP);",
            "  }",
            "  cerrojo.attach(PIN_SERVO);",
            "  cerrojo.write(CERRADO);",
            "  lcd.begin(16, 2);",
            '  linea(0, "Clave:");',
            '  linea(1, "Cerrado");',
            '  Serial.println("TEST:KP=LISTO");',
            '  Serial.println("TEST:CLAVE=ESPERANDO");',
            '  Serial.print("TEST:SERVO=");',
            "  Serial.println(CERRADO);",
            "}",
            "",
            "void loop() {",
            "  char tecla = leerTecla();",
            "  if (tecla == 0) return;",
            '  Serial.print("TEST:TECLA=");',
            "  Serial.println(tecla);",
            "  if (digitos < 4) {",
            "    if (tecla == CLAVE[digitos]) aciertos++;",
            "    digitos++;",
            "    lcd.setCursor(0, 1);",
            "    for (byte i = 0; i < digitos; i++) lcd.print('*');",
            "    for (byte i = digitos; i < 16; i++) lcd.print(' ');",
            "  }",
            "  if (digitos == 4) {",
            "    bool abierta = (aciertos == 4);",
            "    cerrojo.write(abierta ? ABIERTO : CERRADO);",
            '    linea(1, abierta ? "ABIERTO" : "DENEGADO");',
            '    Serial.print("TEST:CLAVE=");',
            '    Serial.println(abierta ? "OK" : "FALLA");',
            '    Serial.print("TEST:SERVO=");',
            "    Serial.println(abierta ? ABIERTO : CERRADO);",
            '    Serial.print("TEST:PANTALLA=");',
            '    Serial.println(abierta ? "ABIERTO" : "DENEGADO");',
            f"    delay({hold_ms});",
            "    cerrojo.write(CERRADO);",
            '    linea(0, "Clave:");',
            '    linea(1, "Cerrado");',
            '    Serial.print("TEST:SERVO=");',
            "    Serial.println(CERRADO);",
            "    digitos = 0;",
            "    aciertos = 0;",
            "  }",
            "}",
            "",
        ]
    )


def gate_counter_sketch(
    step_pin: int = 2,
    run_pin: int = 8,
    segments: tuple[int, ...] = (4, 5, 6, 7, 9, 10, 11),
    button_pin: int = 12,
) -> str:
    """Contador 0-7 lento: el 555 da el pulso y las compuertas lo limpian.

    La cadena es 555 (astable lento) -> AND(reloj, MARCHA) -> OR(boton) ->
    D2. El Uno no genera el pulso: solo cuenta los flancos que llegan por
    ``step_pin`` y pinta el digito en el display de anodo comun (segmento
    en LOW). El AND se arma con NAND + XOR (el XOR con una entrada a 5V es
    el inversor) y el OR con dos NAND, asi que las tres compuertas hacen
    trabajo real y no son adorno.

    ``button_pin`` no se lee en el sketch: el pulsador entra al OR por
    hardware, y el pin solo existe para darle el pull-up interno a ese nodo.

    El oraculo serial imprime ``TEST:DIGITO=<n>`` solo cuando cambia, de
    0 a 7 en ciclo, para que la simulacion muestre el conteo completo.
    """
    pins = tuple(segments)
    for pin in (step_pin, run_pin, button_pin) + pins:
        _validate_pin(pin)
    if len(pins) != 7:
        raise ValueError(f"el display 7 segmentos necesita 7 pines: {pins}")
    if len(set((step_pin, run_pin, button_pin) + pins)) != 10:
        raise ValueError(
            "pines repetidos en el contador de compuertas: "
            f"{(step_pin, run_pin, button_pin) + pins}"
        )

    rows = []
    for digit, pattern in enumerate(SEVEN_SEG_DIGITS[:8]):
        values = ", ".join(str(bit) for bit in pattern)
        rows.append(f"  {{{values}}},  // {digit}")
    table = "\n".join(rows)
    seg_list = ", ".join(str(pin) for pin in pins)
    return "\n".join(
        [
            "// Contador 0-7 lento con reloj 555 y compuertas AND/OR/XOR.",
            "// 555 OUT -> AND(OUT, MARCHA) -> OR(reloj, boton) -> D2.",
            "// El AND sale de NAND + XOR (XOR con una pata a 5V invierte) y el",
            "// OR de dos NAND: las compuertas arman el pulso que cuenta el Uno.",
            "// Display de anodo comun: el comun va a 5V y el segmento enciende",
            "// con LOW (en la placa real, 220 ohmios por segmento).",
            f"const byte PASO = {step_pin};   // pulso del 555 (via compuertas)",
            f"const byte MARCHA = {run_pin}; // enable del AND: HIGH deja pasar",
            f"const byte BOTON = {button_pin};  // pull-up del pulsador (no se lee)",
            f"const byte PINES[7] = {{{seg_list}}};  // a, b, c, d, e, f, g",
            "const byte DIGITOS[8][7] = {",
            table,
            "};",
            "",
            "byte digito = 0;",
            "byte anterior = LOW;",
            "",
            "void mostrar(byte valor) {",
            "  for (byte i = 0; i < 7; i++) {",
            "    digitalWrite(PINES[i], !DIGITOS[valor][i]);",
            "  }",
            "}",
            "",
            "void setup() {",
            "  pinMode(MARCHA, OUTPUT);",
            "  digitalWrite(MARCHA, HIGH);",
            "  pinMode(PASO, INPUT);",
            "  pinMode(BOTON, INPUT_PULLUP);",
            "  for (byte i = 0; i < 7; i++) {",
            "    pinMode(PINES[i], OUTPUT);",
            "  }",
            "  Serial.begin(9600);",
            '  Serial.println("TEST:COMPUERTAS=LISTO");',
            "  mostrar(0);",
            '  Serial.println("TEST:DIGITO=0");',
            "  anterior = digitalRead(PASO);",
            "}",
            "",
            "void loop() {",
            "  byte ahora = digitalRead(PASO);",
            "  if (ahora == HIGH && anterior == LOW) {",
            "    digito = (digito + 1) % 8;",
            "    mostrar(digito);",
            '    Serial.print("TEST:DIGITO=");',
            "    Serial.println(digito);",
            "  }",
            "  anterior = ahora;",
            "}",
            "",
        ]
    )


def contador_jk_sketch(sense_high: bool = False, demo: bool = False,
                       ciclo_pasos: int = 17) -> str:
    """Secuenciador de las cuatro pruebas del taller en un contador 0-7 con JK.

    Pines: D2 reloj (lectura), D3..D5 Q0..Q2, D6 lectura de ng (el Uno R3 no
    tiene A6), D8 EN, D9 RESET (activo en alto), A0..A5 lecturas de na..nf.

    Toda lectura se estabiliza con dos muestras iguales separadas 60 ms: el
    acarreo entre JK es asincrono y el display pasa por estados intermedios.

    ``sense_high`` dice como luce un segmento, o sea que lee el sketch en el
    nodo de la compuerta: en la v1 el display es de **anodo comun** y hay un
    inversor entre la compuerta y el segmento, asi que un segmento encendido
    se lee LOW; en la v2 el display es de **catodo comun** y la compuerta
    maneja el segmento directo, asi que se lee HIGH.

    ``demo`` agrega el conteo en vivo: con ``False`` el sketch termina las
    pruebas en ``setup()`` y deja ``loop()`` vacio, o sea que el display se
    queda en el ultimo digito (0 tras la prueba de reset). Eso fue el "no
    pasa de 0" del 2026-11-15: el circuito contaba y el sketch no lo seguia.
    Con ``True`` el ``loop`` vigila el decodificador y anuncia cada digito
    nuevo, sin inundar el monitor (``DEMO_MAX`` lineas y despues silencio).

    ``ciclo_pasos`` es cuantos valores recorre ``pruebaCiclo`` antes de dar el
    ciclo por bueno. 17 son dos vueltas completas y el rebote; 10 es una
    vuelta (0..7) mas el rebote a 1, que ya prueba los ocho codigos.
    """
    from tinkercad_brain.decoder7 import LIT_TABLE

    if not isinstance(ciclo_pasos, int) or isinstance(ciclo_pasos, bool) or not 2 <= ciclo_pasos <= 17:
        raise ValueError(f"ciclo_pasos debe ser un entero 2..17: {ciclo_pasos!r}")

    encendido = "HIGH" if sense_high else "LOW"
    if sense_high:
        linea_display = (
            "// Display de catodo comun: el comun va a GND y el segmento enciende",
            "// con HIGH. La compuerta maneja el segmento directo (220 ohmios).",
        )
    else:
        linea_display = (
            "// Tabla del taller (1 = segmento encendido). Las compuertas invierten",
            "// para el display de anodo comun, asi que un pin LOW enciende.",
        )
    tabla = ", ".join(f"0x{valor:02X}" for valor in LIT_TABLE)
    secuencia = ", ".join(str(valor % 8) for valor in range(ciclo_pasos))
    cabecera = [
        "// Contador 0-7 con tres 74HC73, reloj 555 y decodificador de compuertas.",
        "// El sketch ejecuta las cuatro pruebas del taller y verifica el",
        "// decodificador contra la tabla de verdad en cada lectura estable.",
    ]
    extras: list[str] = []
    pruebas = [
        "  pulsaReset();",
        "  delay(60);",
        "  int valor = leeEstable();",
        "  verificaDecoder();",
        '  if (valor == 0) Serial.println("TEST:RESET=OK");',
        '  else Serial.println("TEST:RESET=FAIL");',
        "",
        "  digitalWrite(EN, HIGH);",
        '  if (pruebaCiclo()) Serial.println("TEST:CICLO=OK");',
        '  else Serial.println("TEST:CICLO=FAIL");',
        "",
        '  if (pruebaEn0()) Serial.println("TEST:EN0=OK");',
        '  else Serial.println("TEST:EN0=FAIL");',
        "",
        "  int detenido = leeEstable();",
        '  if (pruebaReanuda(detenido)) Serial.println("TEST:REANUDA=OK");',
        '  else Serial.println("TEST:REANUDA=FAIL");',
        "",
        '  if (pruebaResetMedio()) Serial.println("TEST:RESET_MEDIO=OK");',
        '  else Serial.println("TEST:RESET_MEDIO=FAIL");',
        "",
        '  if (decoderOk) Serial.println("TEST:DECODER=OK");',
        '  else Serial.println("TEST:DECODER=FAIL");',
        '  Serial.println("TEST:FIN=OK");',
    ]
    cuerpo_demo: list[str] = ["void loop() {", "  delay(100);", "}"]
    if demo:
        cabecera.append(
            "// El sketch no bloquea el conteo: suelta el contador en el arranque"
        )
        cabecera.append(
            "// y despues solo lee, verifica el decodificador y anuncia cada digito."
        )
        extras = ["const int DEMO_MAX = 12;  // digitos que se anuncian por serial",
                  "int demoCuenta = 0;"]
        cuerpo_demo = [
            "void loop() {",
            "  // El display lo mueve el hardware (555 + JK); el sketch no toca EN",
            "  // ni RESET aqui. Cada digito nuevo se confirma 8 ms despues, porque",
            "  // el acarreo asincrono entre JK deja transitorios de microsegundos.",
            "  static int anterior = -1;",
            "  int valor = leeValor();",
            "  if (valor == anterior) {",
            "    delay(15);",
            "    return;",
            "  }",
            "  delay(8);",
            "  int estable = leeValor();",
            "  if (estable != valor) return;",
            "  anterior = estable;",
            "  verificaDecoder();",
            "  if (demoCuenta < DEMO_MAX) {",
            '    Serial.print("TEST:DIGITO=");',
            "    Serial.println(estable);",
            "    demoCuenta++;",
            '    if (demoCuenta == DEMO_MAX) Serial.println("TEST:DEMO=OK");',
            "  }",
            "}",
        ]
    setup_comun = [
        "void setup() {",
        "  pinMode(CLK, INPUT);",
        "  pinMode(Q0, INPUT);",
        "  pinMode(Q1, INPUT);",
        "  pinMode(Q2, INPUT);",
        "  pinMode(SENSE_G, INPUT);",
        "  for (int i = 0; i < 6; i++) pinMode(SENSE[i], INPUT);",
        "  pinMode(EN, OUTPUT);",
        "  pinMode(RST, OUTPUT);",
        "  digitalWrite(EN, LOW);",
        "  digitalWrite(RST, LOW);",
        "  Serial.begin(9600);",
        '  Serial.println("READY");',
        "",
        "  periodoMs = midePeriodo();",
        '  Serial.print("TEST:PERIODO=");',
        "  Serial.println(periodoMs);",
        "",
    ]
    if demo:
        # El sketch no bloquea el conteo: setup suelta el contador y el loop
        # solo mira. Las cuatro pruebas del taller (RESET, EN, ciclo y reset
        # intermedio) se quedan en la v1: aca movian EN y RESET y dejaban la
        # pantalla en 0 durante toda la medicion.
        cuerpo_setup = [
            *setup_comun,
            "  // Un pulso de RESET deja el contador en 000 y se suelta: de ahi en",
            "  // adelante el conteo lo lleva el hardware, no el sketch.",
            "  pulsaReset();",
            "  delay(60);",
            "  digitalWrite(EN, HIGH);",
            "}",
        ]
    else:
        cuerpo_setup = [*setup_comun, *pruebas, "}"]

    return "\n".join(
        [
            *cabecera,
            "const int CLK = 2;      // salida del 555 (lectura del periodo)",
            "const int Q0 = 3;",
            "const int Q1 = 4;",
            "const int Q2 = 5;",
            "const int SENSE_G = 6;  // el Uno R3 no tiene A6",
            "const int EN = 8;",
            "const int RST = 9;      // activo en alto",
            "const int SENSE[6] = {A0, A1, A2, A3, A4, A5};  // na..nf",
            "",
            *linea_display,
            f"const byte TABLA[8] = {{{tabla}}};",
            "const int SECUENCIA[] = {" + secuencia + "};",
            "",
            "unsigned long periodoMs = 1000;",
            "bool decoderOk = true;",
            *extras,
            "",
            "int leeValor() {",
            "  return (digitalRead(Q2) << 2) | (digitalRead(Q1) << 1) | digitalRead(Q0);",
            "}",
            "",
            "int leeEstable() {",
            "  int a = leeValor();",
            "  delay(60);",
            "  int b = leeValor();",
            "  if (a != b) {",
            "    delay(60);",
            "    return leeValor();",
            "  }",
            "  return b;",
            "}",
            "",
            "byte leeSegmentos() {",
            "  byte mascara = 0;",
            "  for (int i = 0; i < 6; i++) {",
            f"    if (digitalRead(SENSE[i]) == {encendido}) mascara |= (1 << i);",
            "  }",
            f"  if (digitalRead(SENSE_G) == {encendido}) mascara |= (1 << 6);",
            "  return mascara;",
            "}",
            "",
            "// Lee numero y segmentos en la misma ventana: si Q cambia entre las dos",
            "// lecturas de Q, la muestra no sirve (un flanco cayo en medio). Sin esta",
            "// guarda el decoder fallaba por una carrera, no por el cableado.",
            "bool leeEstado(int *valor, byte *mascara) {",
            "  int antes = leeValor();",
            "  byte m = leeSegmentos();",
            "  int despues = leeValor();",
            "  if (antes != despues) return false;",
            "  *valor = despues;",
            "  *mascara = m;",
            "  return true;",
            "}",
            "",
            "void verificaDecoder() {",
            "  for (int intento = 0; intento < 6; intento++) {",
            "    int v;",
            "    byte m;",
            "    if (!leeEstado(&v, &m)) {",
            "      delay(20);",
            "      continue;",
            "    }",
            "    // El acarreo asincrono deja un transitorio de pocos ns: se exige que",
            "    // el numero siga igual 5 ms despues antes de comparar los segmentos.",
            "    delay(5);",
            "    if (leeValor() != v) {",
            "      delay(20);",
            "      continue;",
            "    }",
            "    if (m != TABLA[v]) {",
            "      decoderOk = false;",
            '      Serial.print("TEST:MASK=");',
            "      Serial.print(v);",
            '      Serial.print(",");',
            "      Serial.print(m, HEX);",
            '      Serial.print(",");',
            "      Serial.println(TABLA[v], HEX);",
            "    }",
            "    return;",
            "  }",
            "}",
            "",
            "void esperaFlanco() {",
            "  while (digitalRead(CLK) == HIGH) { }",
            "  while (digitalRead(CLK) == LOW) { }",
            "}",
            "",
            "unsigned long midePeriodo() {",
            "  esperaFlanco();",
            "  unsigned long inicio = millis();",
            "  esperaFlanco();",
            "  return millis() - inicio;",
            "}",
            "",
            *([
                "int esperaCambio(int actual, unsigned long tope) {",
                "  unsigned long inicio = millis();",
                "  while (millis() - inicio < tope) {",
                "    if (leeValor() != actual) return leeEstable();",
                "    delay(20);",
                "  }",
                "  return -1;",
                "}",
                "",
            ] if not demo else []),
            "void pulsaReset() {",
            "  digitalWrite(RST, HIGH);",
            "  delay(80);",
            "  digitalWrite(RST, LOW);",
            "}",
            "",
            *([
                "bool pruebaCiclo() {",
            "  int valor = leeEstable();",
            "  if (valor != 0) return false;",
            f"  for (int i = 1; i < {ciclo_pasos}; i++) {{",
            "    int nuevo = esperaCambio(valor, periodoMs * 2);",
            "    if (nuevo != SECUENCIA[i]) return false;",
            "    verificaDecoder();",
            "    valor = nuevo;",
            "  }",
            "  return true;",
            "}",
            "",
            "bool pruebaEn0() {",
            "  digitalWrite(EN, LOW);",
            "  int valor = leeEstable();",
            "  unsigned long inicio = millis();",
            "  while (millis() - inicio < periodoMs * 3) {",
            "    if (leeValor() != valor) return false;",
            "    delay(50);",
            "  }",
            "  return true;",
            "}",
            "",
            "bool pruebaReanuda(int detenido) {",
            "  digitalWrite(EN, HIGH);",
            "  int nuevo = esperaCambio(detenido, periodoMs * 2);",
            "  return nuevo == ((detenido + 1) & 7);",
            "}",
            "",
            "bool pruebaResetMedio() {",
            "  int valor = leeEstable();",
            "  if (valor == 0) valor = esperaCambio(valor, periodoMs * 2);",
            "  if (valor < 0) return false;",
            "  pulsaReset();",
            "  delay(60);",
            "  return leeEstable() == 0;",
            "}",
            "",
            ] if not demo else []),
            *cuerpo_setup,
            "",
            *([*cuerpo_demo] if demo else ["void loop() {", "  delay(100);", "}"]),
            "",
        ]
    )


def contador_jk_v2_sketch() -> str:
    """El mismo secuenciador sobre la v2: display de catodo comun.

    En la v2 no hay inversores a la salida del decodificador: la compuerta
    maneja el segmento a traves de su resistencia de 220 ohmios, asi que el
    nodo que se lee (y que ve el display) es positivo. Lo unico que cambia
    frente a la v1 es el nivel que significa "encendido".

    Ademas la v2 **cuenta en vivo** (``demo=True``): la v1 se queda mostrando
    el 0 al terminar las pruebas y Eddie lo reporto como "no pasa de 0". Y
    ``pruebaCiclo`` recorre una vuelta mas el rebote en vez de dos vueltas:
    cada paso cuesta un periodo del 555, y el simulador con 30 piezas corre a
    un tercio de la velocidad real, asi que la segunda vuelta solo alargaba la
    espera antes de que el display se quedara contando solo.
    """
    return contador_jk_sketch(sense_high=True, demo=True, ciclo_pasos=10)
