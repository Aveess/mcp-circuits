import json
import re
from pathlib import Path

import pytest

from tinkercad_brain.sketches import (
    blink_sketch,
    button_led_sketch,
    buzzer_button_sketch,
    lcd_counter_sketch,
    lcd_distance_sketch,
    lcd_temp_sketch,
    ldr_led_sketch,
    motor_driver_sketch,
    motor_sketch,
    parking_servo_sketch,
    pin_of_fixture,
    rgb_cycle_sketch,
    servo_knob_sketch,
    tmp36_sketch,
    traffic_sketch,
    ultrasonic_sketch,
)

ROOT = Path(__file__).resolve().parents[1]
REAL_FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"


def _real_fixture(cid):
    circuits = json.loads(REAL_FIXTURES.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == cid)


def _digital_writes(sketch):
    return [(int(pin), level) for pin, level in re.findall(r"digitalWrite\((\d+), (HIGH|LOW)\)", sketch)]


# --- blink ---


def test_blink_default_contains_key_content():
    sketch = blink_sketch()
    assert "pinMode(13, OUTPUT)" in sketch
    assert "Serial.begin(9600)" in sketch
    assert 'Serial.println("READY")' in sketch
    assert "digitalWrite(13, HIGH)" in sketch
    assert "digitalWrite(13, LOW)" in sketch
    assert sketch.count("delay(500)") == 2


def test_blink_custom_pin_and_times_use_literal_pin():
    sketch = blink_sketch(pin=9, on_ms=250, off_ms=750)
    assert "pinMode(9, OUTPUT)" in sketch
    assert "digitalWrite(9, HIGH)" in sketch
    assert "digitalWrite(9, LOW)" in sketch
    assert "delay(250)" in sketch
    assert "delay(750)" in sketch
    assert "13" not in sketch


def test_blink_without_serial_has_no_serial_lines():
    sketch = blink_sketch(serial=False)
    assert "Serial" not in sketch
    assert "pinMode(13, OUTPUT)" in sketch


def test_blink_is_deterministic():
    assert blink_sketch(pin=8, on_ms=100, off_ms=200) == blink_sketch(pin=8, on_ms=100, off_ms=200)


@pytest.mark.parametrize("pin", [0, 1, 14, -1])
def test_blink_rejects_unusable_pins(pin):
    with pytest.raises(ValueError):
        blink_sketch(pin=pin)


@pytest.mark.parametrize("kwargs", [{"on_ms": 0}, {"on_ms": -1}, {"on_ms": 60001}, {"off_ms": 0}, {"off_ms": 60001}])
def test_blink_rejects_out_of_range_times(kwargs):
    with pytest.raises(ValueError):
        blink_sketch(**kwargs)


def test_blink_accepts_boundary_values():
    sketch = blink_sketch(pin=2, on_ms=1, off_ms=60000)
    assert "pinMode(2, OUTPUT)" in sketch
    assert "delay(1)" in sketch
    assert "delay(60000)" in sketch


# --- traffic ---


def test_traffic_default_sequence_turns_off_others_each_phase():
    sketch = traffic_sketch()
    assert "pinMode(11, OUTPUT)" in sketch
    assert "pinMode(10, OUTPUT)" in sketch
    assert "pinMode(9, OUTPUT)" in sketch
    assert "Serial.begin(9600)" in sketch
    assert 'Serial.println("READY")' in sketch
    assert _digital_writes(sketch) == [
        (11, "HIGH"), (10, "LOW"), (9, "LOW"),
        (11, "LOW"), (10, "HIGH"), (9, "LOW"),
        (11, "LOW"), (10, "LOW"), (9, "HIGH"),
    ]
    delays = [int(d) for d in re.findall(r"delay\((\d+)\)", sketch)]
    assert delays == [2000, 700, 2000]


def test_traffic_custom_pins_and_times():
    sketch = traffic_sketch(red=5, yellow=4, green=3, red_ms=100, yellow_ms=50, green_ms=300)
    assert _digital_writes(sketch)[0] == (5, "HIGH")
    assert _digital_writes(sketch)[4] == (4, "HIGH")
    assert _digital_writes(sketch)[-1] == (3, "HIGH")
    assert [int(d) for d in re.findall(r"delay\((\d+)\)", sketch)] == [100, 50, 300]


@pytest.mark.parametrize("kwargs", [{"red": 1}, {"yellow": 14}, {"green": 0}])
def test_traffic_rejects_unusable_pins(kwargs):
    with pytest.raises(ValueError):
        traffic_sketch(**kwargs)


@pytest.mark.parametrize("kwargs", [{"red": 9, "yellow": 9}, {"red": 11, "green": 11}, {"yellow": 10, "green": 10}])
def test_traffic_rejects_repeated_pins(kwargs):
    with pytest.raises(ValueError):
        traffic_sketch(**kwargs)


@pytest.mark.parametrize("kwargs", [{"red_ms": 0}, {"yellow_ms": -5}, {"green_ms": 60001}])
def test_traffic_rejects_out_of_range_times(kwargs):
    with pytest.raises(ValueError):
        traffic_sketch(**kwargs)


# --- rgb_cycle ---


def test_rgb_cycle_default_sequence():
    sketch = rgb_cycle_sketch()
    assert "pinMode(9, OUTPUT)" in sketch
    assert "pinMode(10, OUTPUT)" in sketch
    assert "pinMode(11, OUTPUT)" in sketch
    assert "Serial.begin(9600)" in sketch
    assert 'Serial.println("READY")' in sketch
    assert 'Serial.println("TEST:COLOR=RED")' in sketch
    assert 'Serial.println("TEST:COLOR=GREEN")' in sketch
    assert 'Serial.println("TEST:COLOR=BLUE")' in sketch
    assert _digital_writes(sketch) == [
        (9, "HIGH"), (10, "LOW"), (11, "LOW"),
        (9, "LOW"), (10, "HIGH"), (11, "LOW"),
        (9, "LOW"), (10, "LOW"), (11, "HIGH"),
    ]
    assert [int(d) for d in re.findall(r"delay\((\d+)\)", sketch)] == [900, 900, 900]


def test_rgb_cycle_custom_pins_and_dwell():
    sketch = rgb_cycle_sketch(red=5, green=6, blue=7, dwell_ms=250)
    assert _digital_writes(sketch)[0] == (5, "HIGH")
    assert _digital_writes(sketch)[4] == (6, "HIGH")
    assert _digital_writes(sketch)[-1] == (7, "HIGH")
    assert sketch.count("delay(250)") == 3


def test_rgb_cycle_accepts_boundary_dwell():
    assert rgb_cycle_sketch(dwell_ms=50).count("delay(50)") == 3
    assert rgb_cycle_sketch(dwell_ms=60000).count("delay(60000)") == 3


@pytest.mark.parametrize("kwargs", [{"red": 1}, {"green": 14}, {"blue": 0}])
def test_rgb_cycle_rejects_unusable_pins(kwargs):
    with pytest.raises(ValueError):
        rgb_cycle_sketch(**kwargs)


@pytest.mark.parametrize("kwargs", [{"red": 9, "green": 9}, {"red": 11, "blue": 11}, {"green": 10, "blue": 10}])
def test_rgb_cycle_rejects_repeated_pins(kwargs):
    with pytest.raises(ValueError):
        rgb_cycle_sketch(**kwargs)


@pytest.mark.parametrize("dwell_ms", [0, 49, 60001, -1])
def test_rgb_cycle_rejects_out_of_range_dwell(dwell_ms):
    with pytest.raises(ValueError):
        rgb_cycle_sketch(dwell_ms=dwell_ms)


# --- servo_knob ---


def test_servo_knob_default_contains_key_content():
    sketch = servo_knob_sketch()
    assert "#include <Servo.h>" in sketch
    assert "servo.attach(9)" in sketch
    assert "Serial.begin(9600)" in sketch
    assert 'Serial.println("READY")' in sketch
    assert "analogRead(A0)" in sketch
    assert "map(lectura, 0, 1023, 0, 180)" in sketch
    assert "servo.write(angulo)" in sketch
    assert "TEST:ANGLE=" in sketch
    assert "delay(50)" in sketch


def test_servo_knob_custom_pins():
    sketch = servo_knob_sketch(servo_pin=5, pot_pin="A3")
    assert "servo.attach(5)" in sketch
    assert "analogRead(A3)" in sketch


@pytest.mark.parametrize("servo_pin", [0, 1, 14])
def test_servo_knob_rejects_unusable_servo_pins(servo_pin):
    with pytest.raises(ValueError):
        servo_knob_sketch(servo_pin=servo_pin)


@pytest.mark.parametrize("pot_pin", ["A6", "13", "A-1", "a0", ""])
def test_servo_knob_rejects_unusable_pot_pins(pot_pin):
    with pytest.raises(ValueError):
        servo_knob_sketch(pot_pin=pot_pin)


# --- ultrasonic ---


def test_ultrasonic_default_contains_key_content():
    sketch = ultrasonic_sketch()
    assert "pinMode(7, OUTPUT)" in sketch
    assert "pinMode(6, INPUT)" in sketch
    assert "pinMode(13, OUTPUT)" in sketch
    assert "Serial.begin(9600)" in sketch
    assert 'Serial.println("READY")' in sketch
    assert "delayMicroseconds(2)" in sketch
    assert "delayMicroseconds(10)" in sketch
    assert "pulseIn(6, HIGH)" in sketch
    assert "duracion * 0.034 / 2" in sketch
    assert "TEST:DIST=" in sketch
    assert "digitalWrite(13, distancia < 40.0 ? HIGH : LOW)" in sketch
    assert 'Serial.println(distancia < 40.0 ? "TEST:LED=ON" : "TEST:LED=OFF")' in sketch
    assert "TEST:LED=" in sketch
    assert "delay(200)" in sketch


def test_ultrasonic_custom_pins():
    sketch = ultrasonic_sketch(trig=8, echo=12)
    assert "pinMode(8, OUTPUT)" in sketch
    assert "pinMode(12, INPUT)" in sketch
    assert "pulseIn(12, HIGH)" in sketch


def test_ultrasonic_custom_led_and_threshold():
    sketch = ultrasonic_sketch(trig=8, echo=12, led_pin=9, threshold_cm=25.5)
    assert "pinMode(9, OUTPUT)" in sketch
    assert "digitalWrite(9, distancia < 25.5 ? HIGH : LOW)" in sketch
    assert 'Serial.println(distancia < 25.5 ? "TEST:LED=ON" : "TEST:LED=OFF")' in sketch


def test_ultrasonic_accepts_boundary_thresholds():
    assert "distancia < 2.0" in ultrasonic_sketch(threshold_cm=2.0)
    assert "distancia < 400.0" in ultrasonic_sketch(threshold_cm=400.0)


@pytest.mark.parametrize(
    "kwargs", [{"trig": 0}, {"trig": 14}, {"echo": 0}, {"echo": 14}, {"led_pin": 0}, {"led_pin": 14}]
)
def test_ultrasonic_rejects_unusable_pins(kwargs):
    with pytest.raises(ValueError):
        ultrasonic_sketch(**kwargs)


@pytest.mark.parametrize("threshold_cm", [1.9, 0, -1, 400.1, 1000.0])
def test_ultrasonic_rejects_out_of_range_threshold_cm(threshold_cm):
    with pytest.raises(ValueError):
        ultrasonic_sketch(threshold_cm=threshold_cm)


def test_ultrasonic_rejects_same_trig_and_echo():
    with pytest.raises(ValueError):
        ultrasonic_sketch(trig=7, echo=7)


# --- tmp36 ---


def test_tmp36_default_contains_key_content():
    sketch = tmp36_sketch()
    assert "pinMode(13, OUTPUT)" in sketch
    assert "Serial.begin(9600)" in sketch
    assert 'Serial.println("READY")' in sketch
    assert "analogRead(A0)" in sketch
    assert "lectura * 5.0/1023.0" in sketch
    assert "(volts - 0.5) * 100.0" in sketch
    assert 'Serial.print("TEST:TEMP=");' in sketch
    assert "Serial.println(temp);" in sketch
    assert "digitalWrite(13, temp > 20.0 ? HIGH : LOW)" in sketch
    assert "delay(500)" in sketch


def test_tmp36_custom_pin_analog_and_threshold():
    sketch = tmp36_sketch(pin=8, analog_pin="A2", threshold=30.5)
    assert "pinMode(8, OUTPUT)" in sketch
    assert "analogRead(A2)" in sketch
    assert "digitalWrite(8, temp > 30.5 ? HIGH : LOW)" in sketch


def test_tmp36_threshold_formatting_no_scientific():
    assert "temp > -10.0" in tmp36_sketch(threshold=-10.0)
    assert "temp > 0.5" in tmp36_sketch(threshold=0.5)


def test_tmp36_accepts_boundary_thresholds():
    assert "temp > -40.0" in tmp36_sketch(threshold=-40.0)
    assert "temp > 125.0" in tmp36_sketch(threshold=125.0)


@pytest.mark.parametrize("pin", [0, 1, 14, -1])
def test_tmp36_rejects_unusable_pins(pin):
    with pytest.raises(ValueError):
        tmp36_sketch(pin=pin)


@pytest.mark.parametrize("analog_pin", ["A6", "13", "A-1", "a0", ""])
def test_tmp36_rejects_unusable_analog_pins(analog_pin):
    with pytest.raises(ValueError):
        tmp36_sketch(analog_pin=analog_pin)


@pytest.mark.parametrize("threshold", [-40.1, 125.1, -100.0, 200.0])
def test_tmp36_rejects_out_of_range_thresholds(threshold):
    with pytest.raises(ValueError):
        tmp36_sketch(threshold=threshold)


# --- motor ---


def test_motor_default_contains_key_content():
    sketch = motor_sketch()
    assert "pinMode(9, OUTPUT)" in sketch
    assert "Serial.begin(9600)" in sketch
    assert 'Serial.println("READY")' in sketch
    assert _digital_writes(sketch) == [(9, "HIGH"), (9, "LOW")]
    assert 'Serial.println("TEST:MOTOR=ON")' in sketch
    assert 'Serial.println("TEST:MOTOR=OFF")' in sketch
    assert [int(d) for d in re.findall(r"delay\((\d+)\)", sketch)] == [2000, 1000]


def test_motor_custom_pin():
    sketch = motor_sketch(pin=5)
    assert "pinMode(5, OUTPUT)" in sketch
    assert _digital_writes(sketch) == [(5, "HIGH"), (5, "LOW")]
    assert "pinMode(9" not in sketch


@pytest.mark.parametrize("pin", [0, 1, 14, -1])
def test_motor_rejects_unusable_pins(pin):
    with pytest.raises(ValueError):
        motor_sketch(pin=pin)


# --- motor_driver ---


def test_motor_driver_default_contains_key_content():
    sketch = motor_driver_sketch()
    assert "pinMode(9, OUTPUT)" in sketch
    assert "pinMode(7, OUTPUT)" in sketch
    assert "pinMode(8, OUTPUT)" in sketch
    assert "Serial.begin(9600)" in sketch
    assert 'Serial.println("READY")' in sketch
    assert "analogRead(A0)" in sketch
    assert "map(lectura, 0, 1023, 0, 255)" in sketch
    assert _digital_writes(sketch) == [(7, "HIGH"), (8, "LOW")]
    assert "analogWrite(9, velocidad)" in sketch
    assert 'Serial.print("TEST:SPEED=");' in sketch
    assert "Serial.println(velocidad);" in sketch
    assert "delay(200)" in sketch


def test_motor_driver_custom_pins():
    sketch = motor_driver_sketch(enable_pin=10, in1=5, in2=6, pot_pin="A3")
    assert "pinMode(10, OUTPUT)" in sketch
    assert "analogRead(A3)" in sketch
    assert _digital_writes(sketch) == [(5, "HIGH"), (6, "LOW")]
    assert "analogWrite(10, velocidad)" in sketch


@pytest.mark.parametrize("kwargs", [{"enable_pin": 0}, {"enable_pin": 14}, {"in1": 1}, {"in2": 14}])
def test_motor_driver_rejects_unusable_pins(kwargs):
    with pytest.raises(ValueError):
        motor_driver_sketch(**kwargs)


@pytest.mark.parametrize(
    "kwargs", [{"enable_pin": 9, "in1": 9}, {"enable_pin": 9, "in2": 9}, {"in1": 7, "in2": 7}]
)
def test_motor_driver_rejects_repeated_pins(kwargs):
    with pytest.raises(ValueError):
        motor_driver_sketch(**kwargs)


@pytest.mark.parametrize("pot_pin", ["A6", "13", "A-1", "a0", ""])
def test_motor_driver_rejects_unusable_pot_pins(pot_pin):
    with pytest.raises(ValueError):
        motor_driver_sketch(pot_pin=pot_pin)


# --- button_led ---


def test_button_led_default_contains_key_content():
    sketch = button_led_sketch()
    assert "pinMode(2, INPUT_PULLUP)" in sketch
    assert "pinMode(13, OUTPUT)" in sketch
    assert "Serial.begin(9600)" in sketch
    assert 'Serial.println("READY")' in sketch
    assert "digitalRead(2)" in sketch
    assert "if (estado == LOW)" in sketch
    assert _digital_writes(sketch) == [(13, "HIGH"), (13, "LOW")]
    assert 'Serial.println("TEST:PRESSED")' in sketch
    assert "delay(50)" in sketch


def test_button_led_custom_pins():
    sketch = button_led_sketch(button_pin=3, led_pin=8)
    assert "pinMode(3, INPUT_PULLUP)" in sketch
    assert "pinMode(8, OUTPUT)" in sketch
    assert "digitalRead(3)" in sketch
    assert _digital_writes(sketch) == [(8, "HIGH"), (8, "LOW")]


@pytest.mark.parametrize("kwargs", [{"button_pin": 0}, {"button_pin": 14}, {"led_pin": 1}, {"led_pin": 14}])
def test_button_led_rejects_unusable_pins(kwargs):
    with pytest.raises(ValueError):
        button_led_sketch(**kwargs)


def test_button_led_rejects_same_pins():
    with pytest.raises(ValueError):
        button_led_sketch(button_pin=5, led_pin=5)


# --- buzzer_button ---


def test_buzzer_button_default_contains_key_content():
    sketch = buzzer_button_sketch()
    assert "pinMode(2, INPUT_PULLUP)" in sketch
    assert "Serial.begin(9600)" in sketch
    assert 'Serial.println("READY")' in sketch
    assert "digitalRead(2)" in sketch
    assert "if (estado == LOW)" in sketch
    assert "tone(8, 880)" in sketch
    assert "noTone(8)" in sketch
    assert 'Serial.println("TEST:PRESSED")' in sketch
    assert 'Serial.println("TEST:SILENCIO")' in sketch
    assert "delay(50)" in sketch


def test_buzzer_button_custom_pins_are_literal():
    sketch = buzzer_button_sketch(button_pin=4, buzzer_pin=12)
    assert "pinMode(4, INPUT_PULLUP)" in sketch
    assert "digitalRead(4)" in sketch
    assert "tone(12, 880)" in sketch
    assert "noTone(12)" in sketch
    assert "pinMode(2" not in sketch


def test_buzzer_button_silence_is_the_else_branch():
    sketch = buzzer_button_sketch()
    pressed = sketch.index("tone(8, 880)")
    silence = sketch.index("noTone(8)")
    assert pressed < sketch.index("} else {") < silence


@pytest.mark.parametrize("kwargs", [{"button_pin": 0}, {"button_pin": 14}, {"buzzer_pin": 1}, {"buzzer_pin": 14}])
def test_buzzer_button_rejects_unusable_pins(kwargs):
    with pytest.raises(ValueError):
        buzzer_button_sketch(**kwargs)


def test_buzzer_button_rejects_same_pins():
    with pytest.raises(ValueError):
        buzzer_button_sketch(button_pin=6, buzzer_pin=6)


# --- ldr_led ---


def test_ldr_led_default_contains_key_content():
    sketch = ldr_led_sketch()
    assert "pinMode(13, OUTPUT)" in sketch
    assert "Serial.begin(9600)" in sketch
    assert 'Serial.println("READY")' in sketch
    assert "int luz = analogRead(A0)" in sketch
    assert "if (luz < 300)" in sketch
    assert _digital_writes(sketch) == [(13, "HIGH"), (13, "LOW")]
    assert 'Serial.println("TEST:LED=ON")' in sketch
    assert 'Serial.println("TEST:LED=OFF")' in sketch
    assert 'Serial.print("TEST:LUZ=");' in sketch
    assert "Serial.println(luz);" in sketch
    assert "delay(200)" in sketch


def test_ldr_led_turns_on_when_dark():
    sketch = ldr_led_sketch()
    dark = sketch[sketch.index("if (luz < 300) {") : sketch.index("} else {")]
    assert "digitalWrite(13, HIGH)" in dark
    assert 'Serial.println("TEST:LED=ON")' in dark
    lit = sketch[sketch.index("} else {") : sketch.index('Serial.print("TEST:LUZ=");')]
    assert "digitalWrite(13, LOW)" in lit
    assert 'Serial.println("TEST:LED=OFF")' in lit


def _ldr_branch_for_luz(sketch, luz):
    match = re.search(r"if \(luz ([<>]) (\d+)\) \{", sketch)
    op, umbral = match.group(1), int(match.group(2))
    en_oscuras = luz < umbral if op == "<" else luz > umbral
    if en_oscuras:
        return sketch[match.end() : sketch.index("} else {")]
    return sketch[sketch.index("} else {") : sketch.index('Serial.print("TEST:LUZ=");')]


def test_ldr_led_stays_on_with_low_light():
    # La escena de Tinkercad arranca a oscuras: analogRead ~6 con umbral 300.
    sketch = ldr_led_sketch()
    for luz in (0, 6, 299):
        branch = _ldr_branch_for_luz(sketch, luz)
        assert "digitalWrite(13, HIGH)" in branch
        assert 'Serial.println("TEST:LED=ON")' in branch
    for luz in (300, 500, 1023):
        branch = _ldr_branch_for_luz(sketch, luz)
        assert "digitalWrite(13, LOW)" in branch
        assert 'Serial.println("TEST:LED=OFF")' in branch


def test_ldr_led_documents_voltage_divider():
    sketch = ldr_led_sketch()
    assert "10k" in sketch
    assert "mas luz" in sketch.lower()
    assert "nocturna" in sketch.lower()


def test_ldr_led_custom_pins_and_threshold_are_literal():
    sketch = ldr_led_sketch(ldr_pin="A3", led_pin=8, threshold=700)
    assert "analogRead(A3)" in sketch
    assert "pinMode(8, OUTPUT)" in sketch
    assert "if (luz < 700)" in sketch
    assert _digital_writes(sketch) == [(8, "HIGH"), (8, "LOW")]


def test_ldr_led_accepts_boundary_thresholds():
    assert "if (luz < 0)" in ldr_led_sketch(threshold=0)
    assert "if (luz < 1023)" in ldr_led_sketch(threshold=1023)


@pytest.mark.parametrize("threshold", [-1, 1024, 5000])
def test_ldr_led_rejects_out_of_range_thresholds(threshold):
    with pytest.raises(ValueError):
        ldr_led_sketch(threshold=threshold)


@pytest.mark.parametrize("threshold", [True, False, 500.5, "500", None])
def test_ldr_led_rejects_non_integer_thresholds(threshold):
    with pytest.raises(ValueError):
        ldr_led_sketch(threshold=threshold)


@pytest.mark.parametrize("ldr_pin", ["A6", "13", "a0", "", "D0"])
def test_ldr_led_rejects_unusable_analog_pins(ldr_pin):
    with pytest.raises(ValueError):
        ldr_led_sketch(ldr_pin=ldr_pin)


@pytest.mark.parametrize("led_pin", [0, 1, 14, -1])
def test_ldr_led_rejects_unusable_led_pins(led_pin):
    with pytest.raises(ValueError):
        ldr_led_sketch(led_pin=led_pin)


# --- parking_servo ---


def test_parking_servo_default_contains_key_content():
    sketch = parking_servo_sketch()
    assert "#include <Servo.h>" in sketch
    assert "Servo servo;" in sketch
    assert "servo.attach(9)" in sketch
    assert "pinMode(7, OUTPUT)" in sketch
    assert "pinMode(6, INPUT)" in sketch
    assert "pinMode(10, OUTPUT)" in sketch
    assert "pinMode(11, OUTPUT)" in sketch
    assert "pinMode(3, OUTPUT)" in sketch
    assert "Serial.begin(9600)" in sketch
    assert 'Serial.println("READY")' in sketch
    assert "delayMicroseconds(2)" in sketch
    assert "delayMicroseconds(10)" in sketch
    assert "pulseIn(6, HIGH)" in sketch
    assert "duracion * 0.034 / 2" in sketch
    assert 'Serial.print("TEST:DIST=");' in sketch
    assert "if (distancia < 130.0)" in sketch
    assert 'Serial.println("TEST:ESTADO=ABIERTO")' in sketch
    assert 'Serial.println("TEST:ESTADO=CERRADO")' in sketch
    assert 'Serial.print("TEST:SERVO=");' in sketch
    assert "delay(200)" in sketch


def test_parking_servo_default_threshold_opens_with_measured_scene_distance():
    # La escena real mide ~112 cm; con el default 130 la barrera arranca ABIERTA.
    sketch = parking_servo_sketch()
    assert "if (distancia < 130.0)" in sketch
    open_branch = sketch[sketch.index("if (distancia < 130.0) {") : sketch.index("} else {")]
    assert "angulo = 90" in open_branch
    assert "digitalWrite(11, HIGH)" in open_branch
    assert 'Serial.println("TEST:ESTADO=ABIERTO")' in open_branch
    assert 112 < 130.0


def _parking_branch_for_distance(sketch, distancia):
    match = re.search(r"if \(distancia ([<>]) ([\d.]+)\) \{", sketch)
    op, umbral = match.group(1), float(match.group(2))
    dentro = distancia < umbral if op == "<" else distancia > umbral
    if dentro:
        return sketch[match.end() : sketch.index("} else {")]
    return sketch[sketch.index("} else {") : sketch.index("servo.write(angulo)")]


def test_parking_servo_branch_matches_the_servo_comparison():
    sketch = parking_servo_sketch()
    assert 'TEST:ESTADO=ABIERTO' in _parking_branch_for_distance(sketch, 112.0)
    assert 'TEST:ESTADO=ABIERTO' in _parking_branch_for_distance(sketch, 129.9)
    assert 'TEST:ESTADO=CERRADO' in _parking_branch_for_distance(sketch, 130.0)
    assert 'TEST:ESTADO=CERRADO' in _parking_branch_for_distance(sketch, 300.0)


def test_parking_servo_open_branch_drives_servo_green_and_state():
    sketch = parking_servo_sketch()
    open_branch = sketch[sketch.index("if (distancia < 130.0) {") : sketch.index("} else {")]
    assert "angulo = 90" in open_branch
    assert "digitalWrite(11, HIGH)" in open_branch
    assert "digitalWrite(10, LOW)" in open_branch
    assert "digitalWrite(3, LOW)" in open_branch
    assert 'Serial.println("TEST:ESTADO=ABIERTO")' in open_branch


def test_parking_servo_closed_branch_drives_servo_red_and_state():
    sketch = parking_servo_sketch()
    closed_branch = sketch[sketch.index("} else {") : sketch.index("servo.write(angulo)")]
    assert "angulo = 0" in closed_branch
    assert "digitalWrite(10, HIGH)" in closed_branch
    assert "digitalWrite(11, LOW)" in closed_branch
    assert "digitalWrite(3, LOW)" in closed_branch
    assert 'Serial.println("TEST:ESTADO=CERRADO")' in closed_branch


def test_parking_servo_computes_distance_before_driving_outputs():
    sketch = parking_servo_sketch()
    distance = sketch.index("float distancia = duracion * 0.034 / 2;")
    assert distance < sketch.index("servo.write(angulo)")
    assert distance < sketch.index("digitalWrite(11, HIGH)")
    assert distance < sketch.index("digitalWrite(10, HIGH)")
    assert distance < sketch.index("if (distancia < 130.0)")


def test_parking_servo_prints_distance_before_state():
    sketch = parking_servo_sketch()
    assert sketch.index('Serial.print("TEST:DIST=");') < sketch.index('Serial.println("TEST:ESTADO=ABIERTO")')
    assert sketch.index("Serial.println(distancia);") < sketch.index("if (distancia < 130.0)")


def test_parking_servo_custom_pins_are_literal():
    sketch = parking_servo_sketch(trig=4, echo=5, servo_pin=6, red=12, green=8, blue=2, threshold_cm=35.5)
    assert "pinMode(4, OUTPUT)" in sketch
    assert "pinMode(5, INPUT)" in sketch
    assert "pulseIn(5, HIGH)" in sketch
    assert "servo.attach(6)" in sketch
    assert "pinMode(12, OUTPUT)" in sketch
    assert "pinMode(8, OUTPUT)" in sketch
    assert "pinMode(2, OUTPUT)" in sketch
    assert "if (distancia < 35.5)" in sketch
    assert "pinMode(7, OUTPUT)" not in sketch


def test_parking_servo_accepts_boundary_thresholds():
    assert "if (distancia < 2.0)" in parking_servo_sketch(threshold_cm=2)
    assert "if (distancia < 400.0)" in parking_servo_sketch(threshold_cm=400)


@pytest.mark.parametrize("threshold_cm", [1.9, 0, -1, 401, 400.1, 1000.0])
def test_parking_servo_rejects_out_of_range_thresholds(threshold_cm):
    with pytest.raises(ValueError):
        parking_servo_sketch(threshold_cm=threshold_cm)


@pytest.mark.parametrize("threshold_cm", [True, False, "20", None])
def test_parking_servo_rejects_non_numeric_thresholds(threshold_cm):
    with pytest.raises(ValueError):
        parking_servo_sketch(threshold_cm=threshold_cm)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"trig": 0},
        {"trig": 14},
        {"echo": 1},
        {"echo": 14},
        {"servo_pin": 0},
        {"servo_pin": 14},
        {"red": 1},
        {"green": 14},
        {"blue": 0},
    ],
)
def test_parking_servo_rejects_unusable_pins(kwargs):
    with pytest.raises(ValueError):
        parking_servo_sketch(**kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"trig": 6},
        {"echo": 7},
        {"servo_pin": 7},
        {"red": 11},
        {"green": 10},
        {"blue": 9},
        {"trig": 8, "echo": 8},
    ],
)
def test_parking_servo_rejects_repeated_pins(kwargs):
    with pytest.raises(ValueError):
        parking_servo_sketch(**kwargs)


def test_parking_servo_is_deterministic():
    assert parking_servo_sketch() == parking_servo_sketch()


# --- lcd_counter ---


def test_lcd_counter_default_contains_key_content():
    sketch = lcd_counter_sketch()
    assert "#include <LiquidCrystal.h>" in sketch
    assert "LiquidCrystal lcd(12, 11, 5, 4, 3, 2);" in sketch
    assert "Serial.begin(9600)" in sketch
    assert "lcd.begin(16, 2)" in sketch
    assert "lcd.clear()" in sketch
    assert "lcd.setCursor(0, 0)" in sketch
    assert 'lcd.print("Tinkercad LCD")' in sketch
    assert 'Serial.println("TEST:LCD=LISTO")' in sketch
    assert "lcd.setCursor(0, 1)" in sketch
    assert "delay(1000)" in sketch


def test_lcd_counter_setup_announces_ready_once():
    sketch = lcd_counter_sketch()
    setup = sketch[sketch.index("void setup()") : sketch.index("void loop()")]
    assert setup.count('Serial.println("TEST:LCD=LISTO");') == 1
    assert sketch.count('Serial.println("TEST:LCD=LISTO");') == 1


def test_lcd_counter_title_goes_on_first_row_after_clear():
    sketch = lcd_counter_sketch()
    assert (
        sketch.index("lcd.clear()")
        < sketch.index("lcd.setCursor(0, 0)")
        < sketch.index('lcd.print("Tinkercad LCD")')
    )


def test_lcd_counter_serial_trace_uses_the_displayed_variable():
    sketch = lcd_counter_sketch()
    assert 'snprintf(linea, sizeof(linea), "t=%lus", segundos);' in sketch
    assert "lcd.print(linea);" in sketch
    assert "Serial.println(segundos);" in sketch
    assert sketch.count("segundos = segundos + 1;") == 1
    assert "Serial.println(segundos + " not in sketch
    assert sketch.index("lcd.print(linea);") < sketch.index('Serial.print("TEST:SEG=");')


def test_lcd_counter_pads_the_display_line_to_16_columns():
    sketch = lcd_counter_sketch()
    assert "char linea[17];" in sketch
    assert "for (int i = strlen(linea); i < 16; i++) {" in sketch
    assert "linea[i] = ' ';" in sketch


def test_lcd_counter_documents_contrast_to_ground():
    sketch = lcd_counter_sketch()
    assert "VO" in sketch
    assert "GND" in sketch
    assert "blanco" in sketch


def test_lcd_counter_custom_pins_are_literal():
    sketch = lcd_counter_sketch(rs=8, en=9, d4=10, d5=11, d6=12, d7=13)
    assert "LiquidCrystal lcd(8, 9, 10, 11, 12, 13);" in sketch
    assert "LiquidCrystal lcd(12, 11, 5, 4, 3, 2);" not in sketch


def test_lcd_counter_custom_title_and_period():
    sketch = lcd_counter_sketch(title="Hola", period_ms=250)
    assert 'lcd.print("Hola")' in sketch
    assert "delay(250)" in sketch


def test_lcd_counter_accepts_16_char_title():
    title = "Tinkercad-16char"
    assert len(title) == 16
    assert f'lcd.print("{title}")' in lcd_counter_sketch(title=title)


@pytest.mark.parametrize(
    "title", ["x" * 17, "", 'a"b', "a\\b", "a\nb", "a\rb", "linea\r\n"]
)
def test_lcd_counter_rejects_bad_titles(title):
    with pytest.raises(ValueError):
        lcd_counter_sketch(title=title)


@pytest.mark.parametrize("title", [None, 123, b"titulo", ["titulo"]])
def test_lcd_counter_rejects_non_str_titles(title):
    with pytest.raises(ValueError):
        lcd_counter_sketch(title=title)


@pytest.mark.parametrize("name", ["rs", "en", "d4", "d5", "d6", "d7"])
@pytest.mark.parametrize("pin", [0, 1, 14, -1])
def test_lcd_counter_rejects_unusable_pins(name, pin):
    with pytest.raises(ValueError):
        lcd_counter_sketch(**{name: pin})


@pytest.mark.parametrize("name", ["rs", "en", "d4", "d5", "d6", "d7"])
@pytest.mark.parametrize("pin", [True, False])
def test_lcd_counter_rejects_bool_pins(name, pin):
    with pytest.raises(ValueError):
        lcd_counter_sketch(**{name: pin})


@pytest.mark.parametrize(
    "kwargs",
    [
        {"rs": 11},
        {"en": 12},
        {"d5": 5},
        {"d7": 3},
        {"d4": 2},
        {"rs": 2, "d7": 2},
    ],
)
def test_lcd_counter_rejects_repeated_pins(kwargs):
    with pytest.raises(ValueError):
        lcd_counter_sketch(**kwargs)


@pytest.mark.parametrize("period_ms", [100, 60000])
def test_lcd_counter_accepts_boundary_periods(period_ms):
    assert f"delay({period_ms})" in lcd_counter_sketch(period_ms=period_ms)


@pytest.mark.parametrize("period_ms", [99, 60001, 0, -1, 100.5, "100", None, True])
def test_lcd_counter_rejects_out_of_range_periods(period_ms):
    with pytest.raises(ValueError):
        lcd_counter_sketch(period_ms=period_ms)


def test_lcd_counter_is_deterministic():
    assert lcd_counter_sketch() == lcd_counter_sketch()


# --- lcd_temp ---


def test_lcd_temp_default_contains_key_content():
    sketch = lcd_temp_sketch()
    assert "#include <LiquidCrystal.h>" in sketch
    assert "LiquidCrystal lcd(12, 11, 5, 4, 3, 2);" in sketch
    assert "Serial.begin(9600)" in sketch
    assert "lcd.begin(16, 2)" in sketch
    assert "lcd.clear()" in sketch
    assert "lcd.setCursor(0, 0)" in sketch
    assert 'lcd.print("Temperatura")' in sketch
    assert 'Serial.println("TEST:LCD=LISTO")' in sketch
    assert "lcd.setCursor(0, 1)" in sketch
    assert "delay(500)" in sketch


def test_lcd_temp_uses_the_same_tmp36_formula_as_tmp36_sketch():
    sketch = lcd_temp_sketch()
    reference = tmp36_sketch()
    for line in (
        "float volts = lectura * 5.0/1023.0;",
        "float temp = (volts - 0.5) * 100.0;",
    ):
        assert line in reference
        assert line in sketch
    assert "int lectura = analogRead(A0);" in sketch


def test_lcd_temp_trace_prints_the_same_value_as_the_display():
    sketch = lcd_temp_sketch()
    assert sketch.count("dtostrf(") == 1
    assert "dtostrf(temp, 0, 2, temp_txt);" in sketch
    assert 'snprintf(linea, sizeof(linea), "T=%s C", temp_txt);' in sketch
    assert "lcd.print(linea);" in sketch
    assert "Serial.println(temp_txt);" in sketch
    assert sketch.count("float temp =") == 1
    assert "Serial.println(temp);" not in sketch
    assert sketch.index("lcd.print(linea);") < sketch.index('Serial.print("TEST:TEMP=");')


def test_lcd_temp_formats_two_decimals():
    sketch = lcd_temp_sketch()
    assert "dtostrf(temp, 0, 2, temp_txt);" in sketch
    assert "char temp_txt[8];" in sketch


def test_lcd_temp_pads_the_display_line_to_16_columns():
    sketch = lcd_temp_sketch()
    assert "char linea[17];" in sketch
    assert "for (int i = strlen(linea); i < 16; i++) {" in sketch
    assert "linea[i] = ' ';" in sketch


def test_lcd_temp_documents_simulator_limits():
    sketch = lcd_temp_sketch()
    assert "24.8" in sketch
    assert "VO" in sketch
    assert "GND" in sketch
    assert "blanco" in sketch


def test_lcd_temp_custom_pins_are_literal():
    sketch = lcd_temp_sketch(rs=8, en=9, d4=10, d5=11, d6=12, d7=13)
    assert "LiquidCrystal lcd(8, 9, 10, 11, 12, 13);" in sketch
    assert "LiquidCrystal lcd(12, 11, 5, 4, 3, 2);" not in sketch


def test_lcd_temp_custom_sensor_pin_and_period():
    sketch = lcd_temp_sketch(sensor_pin="A3", period_ms=250)
    assert "analogRead(A3)" in sketch
    assert "analogRead(A0)" not in sketch
    assert "delay(250)" in sketch


@pytest.mark.parametrize("name", ["rs", "en", "d4", "d5", "d6", "d7"])
@pytest.mark.parametrize("pin", [0, 1, 14, -1])
def test_lcd_temp_rejects_unusable_pins(name, pin):
    with pytest.raises(ValueError):
        lcd_temp_sketch(**{name: pin})


@pytest.mark.parametrize("name", ["rs", "en", "d4", "d5", "d6", "d7"])
@pytest.mark.parametrize("pin", [True, False])
def test_lcd_temp_rejects_bool_pins(name, pin):
    with pytest.raises(ValueError):
        lcd_temp_sketch(**{name: pin})


@pytest.mark.parametrize(
    "kwargs",
    [
        {"rs": 11},
        {"en": 12},
        {"d5": 5},
        {"d7": 3},
        {"d4": 2},
        {"rs": 2, "d7": 2},
    ],
)
def test_lcd_temp_rejects_repeated_pins(kwargs):
    with pytest.raises(ValueError):
        lcd_temp_sketch(**kwargs)


@pytest.mark.parametrize("sensor_pin", ["A6", "13", "A-1", "a0", "", 0, None, True])
def test_lcd_temp_rejects_unusable_sensor_pins(sensor_pin):
    with pytest.raises(ValueError):
        lcd_temp_sketch(sensor_pin=sensor_pin)


@pytest.mark.parametrize("period_ms", [200, 60000])
def test_lcd_temp_accepts_boundary_periods(period_ms):
    assert f"delay({period_ms})" in lcd_temp_sketch(period_ms=period_ms)


@pytest.mark.parametrize("period_ms", [199, 60001, 0, -1, 200.5, "200", None, True])
def test_lcd_temp_rejects_out_of_range_periods(period_ms):
    with pytest.raises(ValueError):
        lcd_temp_sketch(period_ms=period_ms)


def test_lcd_temp_is_deterministic():
    assert lcd_temp_sketch() == lcd_temp_sketch()


# --- lcd_distance ---


def test_lcd_distance_default_contains_key_content():
    sketch = lcd_distance_sketch()
    assert "#include <LiquidCrystal.h>" in sketch
    assert "LiquidCrystal lcd(12, 11, 5, 4, 3, 2);" in sketch
    assert "pinMode(7, OUTPUT)" in sketch
    assert "pinMode(6, INPUT)" in sketch
    assert "Serial.begin(9600)" in sketch
    assert "lcd.begin(16, 2)" in sketch
    assert "lcd.clear()" in sketch
    assert "lcd.setCursor(0, 0)" in sketch
    assert 'lcd.print("Distancia")' in sketch
    assert 'Serial.println("TEST:LCD=LISTO")' in sketch
    assert "delayMicroseconds(2)" in sketch
    assert "delayMicroseconds(10)" in sketch
    assert "pulseIn(6, HIGH)" in sketch
    assert 'Serial.print("TEST:DIST=");' in sketch
    assert "TEST:ALARMA=ON" in sketch
    assert "TEST:ALARMA=OFF" in sketch
    assert "delay(300)" in sketch


def test_lcd_distance_uses_the_same_distance_formula_as_ultrasonic_sketch():
    sketch = lcd_distance_sketch()
    reference = ultrasonic_sketch()
    pattern = re.compile(r"float distancia = ([^;]+);")
    assert pattern.search(reference).group(1) == pattern.search(sketch).group(1)
    for line in (
        "long duracion = pulseIn(6, HIGH);",
        "float distancia = duracion * 0.034 / 2;",
    ):
        assert line in reference
        assert line in sketch


def test_lcd_distance_computes_distance_before_anything_is_written():
    sketch = lcd_distance_sketch()
    distance = sketch.index("float distancia = duracion * 0.034 / 2;")
    assert distance < sketch.index("dtostrf(distancia, 0, 1, dist_txt);")
    assert distance < sketch.index("lcd.print(linea);")
    assert distance < sketch.index('Serial.print("TEST:DIST=");')
    assert distance < sketch.index("tone(8, 1000)")
    assert distance < sketch.index("noTone(8)")


def _lcd_distance_branch_for_distance(sketch, distancia):
    match = re.search(r"if \(distancia ([<>]) ([\d.]+)\) \{", sketch)
    op, umbral = match.group(1), float(match.group(2))
    dentro = distancia < umbral if op == "<" else distancia > umbral
    if dentro:
        return sketch[match.end() : sketch.index("} else {")]
    return sketch[sketch.index("} else {") : sketch.index("delay(300)")]


def test_lcd_distance_alarm_trace_lives_in_the_sound_branches():
    sketch = lcd_distance_sketch()
    on_branch = _lcd_distance_branch_for_distance(sketch, 112.0)
    assert "tone(8, 1000)" in on_branch
    assert 'Serial.println("TEST:ALARMA=ON")' in on_branch
    assert "noTone(8)" not in on_branch
    assert "TEST:ALARMA=OFF" not in on_branch

    off_branch = _lcd_distance_branch_for_distance(sketch, 200.0)
    assert "noTone(8)" in off_branch
    assert 'Serial.println("TEST:ALARMA=OFF")' in off_branch
    assert "tone(8, 1000)" not in off_branch
    assert "TEST:ALARMA=ON" not in off_branch


def test_lcd_distance_default_threshold_sounds_the_alarm_in_the_measured_scene():
    # La escena real mide ~112 cm; con el default 130 la alarma arranca ENCENDIDA.
    sketch = lcd_distance_sketch()
    assert "if (distancia < 130.0)" in sketch
    assert 112 < 130.0
    for distancia in (0, 112.0, 129.9):
        assert "TEST:ALARMA=ON" in _lcd_distance_branch_for_distance(sketch, distancia)
    for distancia in (130.0, 200.0, 400.0):
        assert "TEST:ALARMA=OFF" in _lcd_distance_branch_for_distance(sketch, distancia)


def test_lcd_distance_trace_prints_the_same_value_as_the_display():
    sketch = lcd_distance_sketch()
    assert sketch.count("dtostrf(") == 1
    assert "dtostrf(distancia, 0, 1, dist_txt);" in sketch
    assert 'snprintf(linea, sizeof(linea), "D=%s cm", dist_txt);' in sketch
    assert "lcd.print(linea);" in sketch
    assert "Serial.println(dist_txt);" in sketch
    assert sketch.count("float distancia =") == 1
    assert "Serial.println(distancia" not in sketch
    assert sketch.index("lcd.print(linea);") < sketch.index('Serial.print("TEST:DIST=");')


def test_lcd_distance_pads_the_display_line_to_16_columns():
    sketch = lcd_distance_sketch()
    assert "char linea[17];" in sketch
    assert "for (int i = strlen(linea); i < 16; i++) {" in sketch
    assert "linea[i] = ' ';" in sketch


def test_lcd_distance_documents_contrast_and_default_threshold():
    sketch = lcd_distance_sketch()
    assert "VO" in sketch
    assert "GND" in sketch
    assert "blanco" in sketch
    assert "112" in sketch
    assert "observable" in sketch


def test_lcd_distance_custom_pins_are_literal():
    sketch = lcd_distance_sketch(
        trig=4, echo=5, buzzer=9, rs=8, en=10, d4=13, d5=12, d6=11, d7=3
    )
    assert "LiquidCrystal lcd(8, 10, 13, 12, 11, 3);" in sketch
    assert "LiquidCrystal lcd(12, 11, 5, 4, 3, 2);" not in sketch
    assert "pinMode(4, OUTPUT)" in sketch
    assert "pinMode(5, INPUT)" in sketch
    assert "pulseIn(5, HIGH)" in sketch
    assert "tone(9, 1000)" in sketch
    assert "noTone(9)" in sketch
    assert "pinMode(7, OUTPUT)" not in sketch
    assert "pinMode(6, INPUT)" not in sketch


def test_lcd_distance_custom_threshold_and_period():
    sketch = lcd_distance_sketch(threshold_cm=35.5, period_ms=250)
    assert "if (distancia < 35.5)" in sketch
    assert "delay(250)" in sketch


@pytest.mark.parametrize("threshold_cm", [2, 400])
def test_lcd_distance_accepts_boundary_thresholds(threshold_cm):
    assert f"if (distancia < {float(threshold_cm)}" in lcd_distance_sketch(
        threshold_cm=threshold_cm
    )


@pytest.mark.parametrize("threshold_cm", [1.9, 401, 0, 400.1, 1000.0])
def test_lcd_distance_rejects_out_of_range_thresholds(threshold_cm):
    with pytest.raises(ValueError):
        lcd_distance_sketch(threshold_cm=threshold_cm)


@pytest.mark.parametrize("threshold_cm", [True, False, "130", None])
def test_lcd_distance_rejects_non_numeric_thresholds(threshold_cm):
    with pytest.raises(ValueError):
        lcd_distance_sketch(threshold_cm=threshold_cm)


@pytest.mark.parametrize(
    "name", ["trig", "echo", "buzzer", "rs", "en", "d4", "d5", "d6", "d7"]
)
@pytest.mark.parametrize("pin", [0, 1, 14, -1])
def test_lcd_distance_rejects_unusable_pins(name, pin):
    with pytest.raises(ValueError):
        lcd_distance_sketch(**{name: pin})


@pytest.mark.parametrize(
    "name", ["trig", "echo", "buzzer", "rs", "en", "d4", "d5", "d6", "d7"]
)
@pytest.mark.parametrize("pin", [True, False])
def test_lcd_distance_rejects_bool_pins(name, pin):
    with pytest.raises(ValueError):
        lcd_distance_sketch(**{name: pin})


@pytest.mark.parametrize(
    "kwargs",
    [
        {"echo": 7},
        {"buzzer": 7},
        {"rs": 7},
        {"en": 7},
        {"d4": 7},
        {"d5": 7},
        {"d6": 7},
        {"d7": 7},
        {"trig": 2},
        {"buzzer": 8, "d4": 8},
    ],
)
def test_lcd_distance_rejects_repeated_pins(kwargs):
    with pytest.raises(ValueError):
        lcd_distance_sketch(**kwargs)


@pytest.mark.parametrize("period_ms", [100, 60000])
def test_lcd_distance_accepts_boundary_periods(period_ms):
    assert f"delay({period_ms})" in lcd_distance_sketch(period_ms=period_ms)


@pytest.mark.parametrize("period_ms", [99, 60001, 0, -1, 100.5, "300", None, True])
def test_lcd_distance_rejects_out_of_range_periods(period_ms):
    with pytest.raises(ValueError):
        lcd_distance_sketch(period_ms=period_ms)


def test_lcd_distance_is_deterministic():
    assert lcd_distance_sketch() == lcd_distance_sketch()


# --- pin_of_fixture ---


def test_pin_of_fixture_blink_basico_real():
    assert pin_of_fixture(_real_fixture("blink-basico")) == {"led1": 13}


def test_pin_of_fixture_semaforo_real():
    assert pin_of_fixture(_real_fixture("semaforo-3-leds")) == {
        "led_rojo": 11,
        "led_amarillo": 10,
        "led_verde": 9,
    }


def test_pin_of_fixture_omits_led_without_resistor_chain():
    fixture = {
        "nets": [
            ["uno.D13", "r1.1"],
            ["r1.2", "led1.anode"],
            ["uno.D12", "led_suelto.anode"],
            ["r9.2", "led_huerfano.anode"],
        ]
    }
    assert pin_of_fixture(fixture) == {"led1": 13}


def test_pin_of_fixture_handles_reversed_net_order():
    fixture = {"nets": [["r1.1", "uno.D7"], ["led1.anode", "r1.2"]]}
    assert pin_of_fixture(fixture) == {"led1": 7}


def test_pin_of_fixture_without_nets_is_empty():
    assert pin_of_fixture({}) == {}
    assert pin_of_fixture({"nets": []}) == {}
