import json
from pathlib import Path

from tinkercad_brain.fase0.component_map import TYPE_MAP, fixture_type, known_slugs

ROOT = Path(__file__).resolve().parents[1]
REAL_FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"

EXPECTED = {
    "Arduino Uno R3": "arduino-uno",
    "LED": "led",
    "Resistor": "resistor",
    "Pushbutton": "pushbutton",
    "Micro Servo": "servo",
    "Potentiometer": "potentiometer",
    "Ultrasonic Distance Sensor": "ultrasonic-hcsr04",
    "Ultrasonic Distance Sensor (4 Pin)": "ultrasonic-hcsr04",
    "Piezo": "buzzer",
    "Photoresistor": "photoresistor",
    "DC Motor": "dc-motor",
    "RGB LED": "led-rgb-common-cathode",
    "LED RGB": "led-rgb-common-cathode",
    "TMP36": "tmp36",
    "Temperature Sensor [TMP36]": "tmp36",
    "Breadboard Small": "breadboard",
}


def test_map_covers_expected_entries():
    for ezhil_name, slug in EXPECTED.items():
        assert TYPE_MAP[ezhil_name] == slug


def test_every_map_entry_resolves_via_fixture_type():
    for ezhil_name, slug in TYPE_MAP.items():
        assert fixture_type(ezhil_name) == slug


def test_fixture_type_is_case_and_whitespace_insensitive():
    assert fixture_type("arduino uno r3") == "arduino-uno"
    assert fixture_type("  Arduino   Uno   R3  ") == "arduino-uno"
    assert fixture_type("led") == "led"
    assert fixture_type("  rGb   LeD ") == "led-rgb-common-cathode"
    assert fixture_type("\tULTRASONIC   distance   SENSOR\n") == "ultrasonic-hcsr04"


def test_fixture_type_unknown_returns_none():
    assert fixture_type("Componente Inventado") is None
    assert fixture_type("") is None
    assert fixture_type("Arduino") is None


def test_tmp36_real_ezhil_name_resolves_without_duplicate_slug():
    assert fixture_type("Temperature Sensor [TMP36]") == "tmp36"
    assert fixture_type("TMP36") == "tmp36"
    assert known_slugs().count("tmp36") == 1


def test_hcsr04_real_ezhil_name_resolves_without_duplicate_slug():
    assert fixture_type("Ultrasonic Distance Sensor (4 Pin)") == "ultrasonic-hcsr04"
    assert fixture_type("  ultrasonic   distance   sensor (4 pin) ") == "ultrasonic-hcsr04"
    assert fixture_type("Ultrasonic Distance Sensor") == "ultrasonic-hcsr04"
    assert known_slugs().count("ultrasonic-hcsr04") == 1


def test_led_rgb_real_ezhil_name_resolves_without_duplicate_slug():
    # Nombre real ezhil en circuito 6CynuRekrD2.
    assert fixture_type("LED RGB") == "led-rgb-common-cathode"
    assert fixture_type("RGB LED") == "led-rgb-common-cathode"
    assert fixture_type("  led   rgb ") == "led-rgb-common-cathode"
    assert known_slugs().count("led-rgb-common-cathode") == 1


def test_fixture_type_hyphen_underscore_equivalent_to_space():
    assert fixture_type("Ultrasonic Distance Sensor (4-pin)") == "ultrasonic-hcsr04"
    assert fixture_type("Ultrasonic Distance Sensor (4 Pin)") == "ultrasonic-hcsr04"
    assert fixture_type("Ultrasonic Distance Sensor (4 pin)") == "ultrasonic-hcsr04"
    assert fixture_type("Ultrasonic Distance Sensor (4_pin)") == "ultrasonic-hcsr04"


def test_known_slugs_are_unique_and_sorted():
    slugs = known_slugs()
    assert slugs == sorted(set(slugs))
    assert set(EXPECTED.values()) <= set(slugs)


def test_known_slugs_consistent_with_real_fixtures():
    circuits = json.loads(REAL_FIXTURES.read_text(encoding="utf-8"))
    fixture_types = {
        component["type"]
        for circuit in circuits
        for component in circuit["components"]
    }
    slugs = set(known_slugs())
    # Slugs básicos que las fixtures usan deben estar en el mapa canónico.
    assert {"arduino-uno", "led", "resistor"} <= slugs
    assert {"arduino-uno", "led", "resistor"} <= fixture_types
    # Todo slug del mapa presente en fixtures es un type real de fixtures o breadboard.
    for slug in slugs & fixture_types:
        assert slug in fixture_types or slug == "breadboard"
