import json
import re
from pathlib import Path

import pytest

from tinkercad_brain.sketches import (
    blink_sketch,
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
    assert "Serial.begin(9600)" in sketch
    assert 'Serial.println("READY")' in sketch
    assert "delayMicroseconds(2)" in sketch
    assert "delayMicroseconds(10)" in sketch
    assert "pulseIn(6, HIGH)" in sketch
    assert "duracion * 0.034 / 2" in sketch
    assert "TEST:DIST=" in sketch
    assert "delay(200)" in sketch


def test_ultrasonic_custom_pins():
    sketch = ultrasonic_sketch(trig=8, echo=12)
    assert "pinMode(8, OUTPUT)" in sketch
    assert "pinMode(12, INPUT)" in sketch
    assert "pulseIn(12, HIGH)" in sketch


@pytest.mark.parametrize("kwargs", [{"trig": 0}, {"trig": 14}, {"echo": 0}, {"echo": 14}])
def test_ultrasonic_rejects_unusable_pins(kwargs):
    with pytest.raises(ValueError):
        ultrasonic_sketch(**kwargs)


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
    assert "digitalWrite(13, temp > 25.0 ? HIGH : LOW)" in sketch
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
