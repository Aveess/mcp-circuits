from tinkercad_brain.fase0.normalize import normalize_circuit


def _comp(type_, instance_id):
    return {"type": type_, "instance_id": instance_id, "pins": []}


def test_blink_completo():
    inspect_data = {
        "components": [
            {**_comp("Arduino Uno R3", "uno_260"), "pins": [{"name": "D13"}, {"name": "GND1"}]},
            {**_comp("LED", "led_260"), "pins": [{"name": "anode"}, {"name": "cathode"}]},
            {**_comp("Resistor", "r_260"), "pins": [{"name": "1"}, {"name": "2"}]},
        ]
    }
    schematic_data = {
        "nets": [
            {"pins": [{"component": "Arduino Uno R3", "pin": "D13"}, {"component": "Resistor", "pin": "1"}]},
            {"pins": [{"component": "Resistor", "pin": "2"}, {"component": "LED", "pin": "anode"}]},
            {"pins": [{"component": "LED", "pin": "cathode"}, {"component": "Arduino Uno R3", "pin": "GND1"}]},
        ]
    }

    assert normalize_circuit(inspect_data, schematic_data) == {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "led1", "type": "led"},
            {"ref": "r1", "type": "resistor"},
        ],
        "nets": [["uno.D13", "r1.1"], ["r1.2", "led1.anode"], ["led1.cathode", "uno.GND1"]],
    }


def test_dos_leds_numerados_en_orden():
    inspect_data = {
        "components": [
            _comp("Arduino Uno R3", "uno_1"),
            _comp("LED", "led_a"),
            _comp("LED", "led_b"),
        ]
    }

    assert normalize_circuit(inspect_data, {"nets": []}) == {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "led1", "type": "led"},
            {"ref": "led2", "type": "led"},
        ],
        "nets": [],
    }


def test_tipo_desconocido_usa_slug():
    inspect_data = {"components": [_comp("Breadboard Small", "bb_1")]}

    assert normalize_circuit(inspect_data, {"nets": []}) == {
        "components": [{"ref": "breadboard1", "type": "breadboard"}],
        "nets": [],
    }


def test_net_con_componente_ausente_se_omite():
    inspect_data = {
        "components": [_comp("Arduino Uno R3", "uno_1"), _comp("Resistor", "r_1")]
    }
    schematic_data = {
        "nets": [
            {"pins": [{"component": "Arduino Uno R3", "pin": "D13"}, {"component": "LED", "pin": "anode"}]},
            {
                "pins": [
                    {"component": "Arduino Uno R3", "pin": "D13"},
                    {"component": "Resistor", "pin": "1"},
                    {"component": "LED", "pin": "anode"},
                ]
            },
        ]
    }

    assert normalize_circuit(inspect_data, schematic_data) == {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "r1", "type": "resistor"},
        ],
        "nets": [["uno.D13", "r1.1"]],
    }


def test_entrada_vacia():
    assert normalize_circuit({}, {}) == {"components": [], "nets": []}
    assert normalize_circuit({"components": []}, {"nets": []}) == {"components": [], "nets": []}
