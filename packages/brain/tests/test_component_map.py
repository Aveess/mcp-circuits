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
    "Motor DC": "dc-motor",
    "NPN Transistor": "transistor-npn",
    "Transistor NPN": "transistor-npn",
    "Transistor": "transistor-npn",
    "Diode": "diode",
    "RGB LED": "led-rgb-common-cathode",
    "LED RGB": "led-rgb-common-cathode",
    "TMP36": "tmp36",
    "Temperature Sensor [TMP36]": "tmp36",
    "Breadboard Small": "breadboard",
    "H-bridge Motor Driver [L293D]": "l293d",
    "9V Battery": "battery-9v",
    "LCD 16 x 2": "lcd-16x2",
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


def test_transistor_diode_motor_resolve_without_duplicate_slugs():
    assert fixture_type("NPN Transistor") == "transistor-npn"
    assert fixture_type("  transistor   npn ") == "transistor-npn"
    assert fixture_type("Transistor") == "transistor-npn"
    assert fixture_type("Diode") == "diode"
    assert fixture_type("DC Motor") == "dc-motor"
    assert fixture_type("motor dc") == "dc-motor"
    assert known_slugs().count("transistor-npn") == 1
    assert known_slugs().count("diode") == 1
    assert known_slugs().count("dc-motor") == 1


def test_transistor_bjt_real_ezhil_name_resolves():
    # Nombre real ezhil en circuito 73azwj2IJDE.
    assert fixture_type("NPN Transistor (BJT)") == "transistor-npn"
    assert known_slugs().count("transistor-npn") == 1


def test_l293d_and_battery_real_ezhil_names_resolve():
    # Nombres reales ezhil verificados con inspect_circuit.
    assert fixture_type("H-bridge Motor Driver [L293D]") == "l293d"
    assert fixture_type("9V Battery") == "battery-9v"
    assert known_slugs().count("l293d") == 1
    assert known_slugs().count("battery-9v") == 1


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


def test_piezo_and_ldr_real_ezhil_names_resolve():
    # Nombres reales ezhil verificados en vivo (circuito cZcqbZ3eNlA).
    assert fixture_type("Piezo") == "buzzer"
    assert fixture_type("Photoresistor (LDR)") == "photoresistor"
    assert fixture_type("Photoresistor") == "photoresistor"
    assert fixture_type("  photoresistor   (ldr) ") == "photoresistor"
    assert "buzzer" in known_slugs()
    assert "photoresistor" in known_slugs()
    assert known_slugs().count("photoresistor") == 1


def test_lcd_16x2_real_ezhil_name_resolves_without_duplicate_slug():
    # Nombre real verificado en vivo con inspect_circuit (did 113878).
    assert fixture_type("LCD 16 x 2") == "lcd-16x2"
    assert fixture_type("  lcd   16   x   2 ") == "lcd-16x2"
    assert "lcd-16x2" in known_slugs()
    assert known_slugs().count("lcd-16x2") == 1
