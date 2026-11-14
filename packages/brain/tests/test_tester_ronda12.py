"""Tester independiente ronda 12: piezo, LDR y barrera de parking.

Contratos juzgados sin repetir los tests de produccion:

- Refs: para el MISMO dict de inspect, ``derive_nets`` y
  ``normalize_circuit`` deben numerar cada instancia igual (el bug de esta
  ronda era "ldr1" en nets vs "photoresistor1" en components, que dejaba
  la conectividad en 0.66). Se verifica por instancia, no solo por tipo.
- Punta a punta sin Tinkercad: se emula el inspect que devolveria el
  puente (wires del model call + un wire pin->hueco por pata, como en los
  logs vivos) y se exige ``compare_connectivity == 1.0``.
- Builder: ancla de piezo distinta de "positive" o de LDR distinta de "1"
  tiene que explotar con BuildError, nunca rutear con geometria supuesta.
- Layout: el bloque LDR+divisor no se parte (o entran los dos o ninguno);
  con dos resistencias en el nodo medio la eleccion es determinista; el
  piezo no retrocede si el cursor ya paso su columna minima.
- Sketches: la traza TEST:LED y el digitalWrite del LDR son la MISMA
  comparacion (incluido el borde luz == umbral); en parking TEST:ESTADO
  vive en las mismas ramas que el angulo del servo y la distancia se
  calcula antes de escribir.
"""
import copy
import json
import re
from pathlib import Path

import pytest

from tinkercad_brain import builder as builder_module
from tinkercad_brain.breadboard_nets import derive_nets
from tinkercad_brain.builder import (
    DID_BY_TYPE,
    BuildError,
    _translate_endpoint,
    fixture_to_model_call,
)
from tinkercad_brain.fase0.fixtures import load_fixtures
from tinkercad_brain.fase0.metrics import compare_connectivity
from tinkercad_brain.fase0.normalize import normalize_circuit
from tinkercad_brain.layout import plan_layout
from tinkercad_brain.sketches import (
    buzzer_button_sketch,
    ldr_led_sketch,
    parking_servo_sketch,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_PATH = ROOT / "fixtures" / "fase0" / "circuits.json"
NEW_FIXTURES = ("buzzer-activo", "ldr-divisor", "parking-servo-ultrasonico-rgb")


def _fixture(fixture_id):
    circuits = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == fixture_id)


def _col(at):
    return int(at[:-1])


def _holes(fixture, ref, pins=None):
    """Huecos reales de cada pin de ``ref`` segun layout + builder."""
    layout = plan_layout(fixture)
    placements = layout["placements"]
    type_by_ref = {c["ref"]: c["type"] for c in fixture["components"]}
    if pins is None:
        pins = {
            endpoint.split(".", 1)[1]
            for net in fixture["nets"]
            for endpoint in net
            if endpoint.split(".", 1)[0] == ref
        }
    return {
        pin: _translate_endpoint(f"{ref}.{pin}", placements, type_by_ref)
        for pin in sorted(pins)
    }


# --------------------------------------------------------------- fixtures

@pytest.mark.parametrize("fixture_id", NEW_FIXTURES)
def test_r12_fixtures_nuevas_cargan_y_tienen_los_componentes_esperados(fixture_id):
    circuits = load_fixtures(FIXTURES_PATH)
    fixture = next(c for c in circuits if c["id"] == fixture_id)
    types = [c["type"] for c in fixture["components"]]
    expected = {
        "buzzer-activo": ["arduino-uno", "buzzer", "pushbutton"],
        "ldr-divisor": [
            "arduino-uno", "photoresistor", "resistor", "led", "resistor",
        ],
        "parking-servo-ultrasonico-rgb": [
            "arduino-uno", "led-rgb-common-cathode", "resistor", "resistor",
            "resistor", "servo", "ultrasonic-hcsr04",
        ],
    }[fixture_id]
    assert sorted(types) == sorted(expected)


# --------------------------------------------- refs: nets vs components

# Pin real que Tinkercad reporta en wires/componentes -> pin de fixture.
# Tabla propia del tester (no se importa de produccion).
_REAL_PIN = {
    "led": {"Anode": "anode", "Cathode": "cathode"},
    "resistor": {"Terminal 1": "1", "Terminal 2": "2"},
    "photoresistor": {"terminal-1": "1", "terminal-2": "2"},
    "buzzer": {"Positive": "positive", "Negative": "negative"},
    "pushbutton": {"Terminal 2b": "1", "Terminal 1a": "2"},
    "servo": {"Ground": "gnd", "Power": "vcc", "Signal": "signal"},
    "ultrasonic-hcsr04": {
        "Power": "vcc", "Trigger": "trig", "Echo": "echo", "Ground": "gnd",
    },
    "led-rgb-common-cathode": {
        "Red": "red", "Green": "green", "Blue": "blue", "Cathode": "cathode",
    },
}

# Inverso: pin de fixture -> nombre real que reporta Tinkercad.
_FIXTURE_PIN = {
    ctype: {fixture_pin: real for real, fixture_pin in pins.items()}
    for ctype, pins in _REAL_PIN.items()
}

_CANONICAL_BY_RAW = {
    "Arduino Uno R3": "arduino-uno",
    "Photoresistor (LDR)": "photoresistor",
    "Piezo": "buzzer",
    "Resistor": "resistor",
    "LED": "led",
    "Pushbutton": "pushbutton",
}

_RAW_TYPE = {
    "led": "LED",
    "resistor": "Resistor",
    "photoresistor": "Photoresistor (LDR)",
    "buzzer": "Piezo",
    "pushbutton": "Pushbutton",
    "servo": "Micro Servo",
    "ultrasonic-hcsr04": "Ultrasonic Distance Sensor (4-pin)",
    "led-rgb-common-cathode": "LED RGB",
}


def _ep(component, pin, instance_id):
    return {"component": component, "pin": pin, "instance_id": instance_id}


def _refs_inspect_ldr_piezo():
    """Inspect con LDR, piezo, dos resistencias, LED y boton."""
    components = [
        {"type": "Arduino Uno R3", "instance_id": "uno1", "pins": []},
        {"type": "Breadboard Small", "instance_id": "bb1", "pins": []},
        {"type": "Photoresistor (LDR)", "instance_id": "ldr_a", "pins": []},
        {"type": "Piezo", "instance_id": "pz_a", "pins": []},
        {"type": "Resistor", "instance_id": "rs_a", "pins": []},
        {"type": "Resistor", "instance_id": "rs_b", "pins": []},
        {"type": "LED", "instance_id": "led_a", "pins": []},
        {"type": "Pushbutton", "instance_id": "btn_a", "pins": []},
    ]
    bb = "Breadboard Small"
    uno = "Arduino Uno R3"
    wires = [
        # LDR arriba (5V), nodo medio con la resistencia divisora, GND.
        {"source": _ep(uno, "5V", "uno1"), "target": _ep(bb, "a1", "bb1")},
        {"source": _ep("Photoresistor (LDR)", "terminal-1", "ldr_a"),
         "target": _ep(bb, "e1", "bb1")},
        {"source": _ep("Photoresistor (LDR)", "terminal-2", "ldr_a"),
         "target": _ep(bb, "e2", "bb1")},
        {"source": _ep(uno, "A0", "uno1"), "target": _ep(bb, "e2", "bb1")},
        {"source": _ep("Resistor", "Terminal 1", "rs_a"),
         "target": _ep(bb, "e3", "bb1")},
        {"source": _ep(uno, "A0", "uno1"), "target": _ep(bb, "e3", "bb1")},
        {"source": _ep("Resistor", "Terminal 2", "rs_a"),
         "target": _ep(bb, "e7", "bb1")},
        {"source": _ep(uno, "GND", "uno1"), "target": _ep(bb, "e7", "bb1")},
        # Piezo con terminales Positive/Negative (como los wires vivos).
        {"source": _ep("Piezo", "Positive", "pz_a"),
         "target": _ep(bb, "a5", "bb1")},
        {"source": _ep(uno, "D8", "uno1"), "target": _ep(bb, "a5", "bb1")},
        {"source": _ep("Piezo", "Negative", "pz_a"),
         "target": _ep(bb, "a10", "bb1")},
        {"source": _ep(uno, "GND", "uno1"), "target": _ep(bb, "a10", "bb1")},
        # LED con resistencia en serie.
        {"source": _ep("Resistor", "Terminal 1", "rs_b"),
         "target": _ep(bb, "f2", "bb1")},
        {"source": _ep(uno, "D13", "uno1"), "target": _ep(bb, "f2", "bb1")},
        {"source": _ep("Resistor", "Terminal 2", "rs_b"),
         "target": _ep(bb, "f6", "bb1")},
        {"source": _ep("LED", "Anode", "led_a"), "target": _ep(bb, "f6", "bb1")},
        {"source": _ep("LED", "Cathode", "led_a"),
         "target": _ep(bb, "f7", "bb1")},
        {"source": _ep(uno, "GND", "uno1"), "target": _ep(bb, "f7", "bb1")},
        # Boton.
        {"source": _ep("Pushbutton", "Terminal 2b", "btn_a"),
         "target": _ep(bb, "a15", "bb1")},
        {"source": _ep(uno, "D2", "uno1"), "target": _ep(bb, "a15", "bb1")},
    ]
    return {"components": components, "wires": wires}


def test_r12_nets_y_components_numeran_cada_instancia_igual():
    inspect = _refs_inspect_ldr_piezo()
    normalized = normalize_circuit(inspect, {"nets": []})
    nets = derive_nets(inspect)

    # normalize emite un componente por componente real, en el orden del
    # inspect: se puede mapear instance_id -> (ref, tipo) sin replicar
    # contadores.
    real = [c for c in inspect["components"] if "Breadboard" not in c["type"]]
    normalized_components = normalized["components"]
    assert len(real) == len(normalized_components)
    ref_by_instance = {}
    canonical_by_instance = {}
    for component, norm in zip(real, normalized_components):
        ref_by_instance[component["instance_id"]] = norm["ref"]
        canonical_by_instance[component["instance_id"]] = norm["type"]

    # El LDR tiene que salir con el MISMO prefijo que normalize.
    assert ref_by_instance["ldr_a"] == "photoresistor1"
    assert "ldr1" not in {e.split(".", 1)[0] for net in nets for e in net}

    # Cada pata cableada de cada instancia aparece bajo EL ref que le dio
    # normalize a esa instancia (no bajo el de otra).
    pins_by_instance = {}
    for wire in inspect["wires"]:
        for side in (wire["source"], wire["target"]):
            iid = side["instance_id"]
            if iid in ref_by_instance:
                pins_by_instance.setdefault(iid, set()).add(side["pin"])
    assert set(pins_by_instance) == set(ref_by_instance)
    derived = {e for net in nets for e in net}
    for iid, real_pins in pins_by_instance.items():
        ctype = canonical_by_instance[iid]
        ref = ref_by_instance[iid]
        for real_pin in real_pins:
            if ctype == "arduino-uno":
                fixture_pin = "GND1" if real_pin == "GND" else real_pin
            else:
                fixture_pin = _REAL_PIN[ctype][real_pin]
            assert f"{ref}.{fixture_pin}" in derived


# ------------------------- punta a punta sin Tinkercad (geometria + refs)

def _emulate_inspect(fixture):
    """Inspect que devolveria el puente tras construir la fixture.

    Usa los placements reales del layout, los offsets del builder y los
    wires del model call; agrega el wire pin->hueco que el puente crea
    al colocar cada parte (asi se ve en live6/live14/live21).
    """
    layout = plan_layout(fixture)
    assert layout["unplaced"] == [], layout["unplaced"]
    placements = layout["placements"]
    type_by_ref = {c["ref"]: c["type"] for c in fixture["components"]}
    call = fixture_to_model_call(fixture)

    components = [
        {"type": "Arduino Uno R3", "instance_id": "uno1", "pins": []},
        {"type": "Breadboard Small", "instance_id": "bb1", "pins": []},
    ]
    instance_by_ref = {}
    for part in call["parts"]:
        ref = part["ref"]
        ctype = type_by_ref[ref]
        assert ctype in _RAW_TYPE, ctype
        instance_by_ref[ref] = f"i{len(components)}"
        components.append(
            {"type": _RAW_TYPE[ctype], "instance_id": instance_by_ref[ref],
             "pins": []}
        )

    wires = []
    # Pata -> hueco (lo que el puente agrega al colocar la parte).
    for ref, ctype in type_by_ref.items():
        if ctype == "arduino-uno" or ref not in placements:
            continue
        pins = {
            endpoint.split(".", 1)[1]
            for net in fixture["nets"]
            for endpoint in net
            if endpoint.split(".", 1)[0] == ref
        }
        for pin in sorted(pins):
            hole = _translate_endpoint(f"{ref}.{pin}", placements, type_by_ref)
            wires.append(
                (
                    instance_by_ref[ref],
                    _FIXTURE_PIN[ctype][pin],
                    "bb1",
                    hole,
                )
            )
    # Wires del model call: extremos ya traducidos a hueco o pin del Uno.
    for wire in call["wires"]:
        endpoints = []
        for text in (wire["from"], wire["to"]):
            if text.startswith("uno."):
                endpoints.append(("uno1", text.split(".", 1)[1]))
            elif re.fullmatch(r"\d+[a-j]", text):
                endpoints.append(("bb1", text))
            else:
                ref, _, pin = text.partition(".")
                assert ref in instance_by_ref, (ref, text)
                ctype = type_by_ref[ref]
                endpoints.append(
                    (instance_by_ref[ref], _FIXTURE_PIN[ctype][pin])
                )
        (src_inst, src_pin), (dst_inst, dst_pin) = endpoints
        wires.append((src_inst, src_pin, dst_inst, dst_pin))

    inspect_wires = [
        {"source": _ep("", pin, inst), "target": _ep("", pin2, inst2)}
        for inst, pin, inst2, pin2 in wires
    ]
    # component = instance_id para que _resolve lo encuentre sin ambiguedad.
    for wire in inspect_wires:
        wire["source"]["component"] = wire["source"]["instance_id"]
        wire["target"]["component"] = wire["target"]["instance_id"]
    return {"components": components, "wires": inspect_wires}


def _fidelity(fixture):
    inspect = _emulate_inspect(fixture)
    normalized = normalize_circuit(inspect, {"nets": []})
    actual = {
        "components": normalized["components"],
        "nets": derive_nets(inspect),
    }
    expected = {
        "components": fixture["components"],
        "nets": fixture["nets"],
    }
    return compare_connectivity(expected, actual)


@pytest.mark.parametrize("fixture_id", NEW_FIXTURES)
def test_r12_conectividad_extremo_a_extremo_es_1_0(fixture_id):
    result = _fidelity(_fixture(fixture_id))
    assert result["shorts"] == []
    assert result["missing_components"] == []
    assert result["connectivity_score"] == 1.0
    assert result["score"] == 1.0


def test_r12_ldr_divisor_emulado_conserva_el_nodo_medio():
    fixture = _fixture("ldr-divisor")
    inspect = _emulate_inspect(fixture)
    nets = derive_nets(inspect)
    middle = [net for net in nets if "uno.A0" in net]
    assert len(middle) == 1
    assert "photoresistor1.2" in middle[0]
    assert "r2.1" in middle[0]
    # La pata 1 del LDR va a 5V y la 2 no queda puenteada con la 1.
    assert any("photoresistor1.1" in net and "uno.5V" in net for net in nets)
    assert not any(
        {"photoresistor1.1", "photoresistor1.2"} <= set(net) for net in nets
    )


@pytest.mark.parametrize("fixture_id", NEW_FIXTURES)
def test_r12_layout_no_muta_la_fixture(fixture_id):
    fixture = _fixture(fixture_id)
    before = copy.deepcopy(fixture)
    plan_layout(fixture)
    assert fixture == before


# ------------------------------------------------ builder: ancla ruidosa

def _patched_layout(monkeypatch, overrides):
    """Fuerza placements por ref manteniendo el resto del layout real."""
    real_plan_layout = builder_module.plan_layout

    def patched(fixture):
        layout = real_plan_layout(fixture)
        placements = {ref: dict(p) for ref, p in layout["placements"].items()}
        for ref, changes in overrides.items():
            if ref in placements:
                placements[ref].update(changes)
        return {"placements": placements, "unplaced": list(layout["unplaced"])}

    monkeypatch.setattr(builder_module, "plan_layout", patched)


@pytest.mark.parametrize(
    "fixture_id, ref, bad_pin",
    [
        ("buzzer-activo", "buzzer1", "negative"),
        ("buzzer-activo", "buzzer1", "1"),
        ("ldr-divisor", "ldr1", "terminal-1"),
        ("ldr-divisor", "ldr1", "2"),
    ],
)
def test_r12_ancla_inesperada_de_piezo_o_ldr_es_build_error(
    monkeypatch, fixture_id, ref, bad_pin
):
    _patched_layout(monkeypatch, {ref: {"pin": bad_pin}})
    with pytest.raises(BuildError, match="ancla") as excinfo:
        fixture_to_model_call(_fixture(fixture_id))
    assert ref in str(excinfo.value)


def test_r12_anclas_reales_de_piezo_y_ldr_en_parts_y_huecos():
    buzzer = _fixture("buzzer-activo")
    parts = {p["ref"]: p for p in fixture_to_model_call(buzzer)["parts"]}
    assert parts["buzzer1"]["did"] == 114067
    assert parts["buzzer1"]["pin"] == "+"
    assert parts["buzzer1"]["at"] == "24e"
    assert parts["buzzer1"]["angle"] == 0
    assert _holes(buzzer, "buzzer1", pins=["positive", "negative"]) == {
        "positive": "24e", "negative": "29e",
    }

    ldr = _fixture("ldr-divisor")
    parts = {p["ref"]: p for p in fixture_to_model_call(ldr)["parts"]}
    assert parts["ldr1"]["did"] == 116691
    assert parts["ldr1"]["pin"] == "terminal-1"
    assert _holes(ldr, "ldr1") == {"1": "22e", "2": "23e"}
    assert _holes(ldr, "r2", pins=["1", "2"]) == {"1": "25e", "2": "29e"}
    assert DID_BY_TYPE["buzzer"] == 114067
    assert DID_BY_TYPE["photoresistor"] == 116691


# ------------------------------------------------------- layout: piezo

def _led_blocks(count):
    components = [{"ref": "uno", "type": "arduino-uno"}]
    nets = []
    for i in range(1, count + 1):
        components += [
            {"ref": f"led{i}", "type": "led"},
            {"ref": f"r{i}", "type": "resistor"},
        ]
        nets.append([f"r{i}.2", f"led{i}.anode"])
    return components, nets


def test_r12_buzzer_activo_boton_antes_del_piezo_y_sin_compartir_columna():
    fixture = _fixture("buzzer-activo")
    result = plan_layout(fixture)
    assert result["unplaced"] == []
    btn_col = _col(result["placements"]["btn1"]["at"])
    buzzer_col = _col(result["placements"]["buzzer1"]["at"])
    assert buzzer_col >= 24
    assert btn_col < buzzer_col
    assert set(range(buzzer_col, buzzer_col + 6)).isdisjoint({btn_col})
    # El piezo y su pata negativa caen dentro de la protoboard.
    holes = _holes(fixture, "buzzer1")
    assert _col(holes["negative"]) - _col(holes["positive"]) == 5
    assert _col(holes["negative"]) <= 30


def test_r12_piezo_con_cursor_25_no_retrocede_y_usa_hasta_la_columna_30():
    components, nets = _led_blocks(4)  # cursor tras 4 bloques: 25
    components.append({"ref": "buzzer1", "type": "buzzer"})
    result = plan_layout({"components": components, "nets": nets})

    assert result["unplaced"] == []
    assert result["placements"]["buzzer1"] == {
        "at": "25e", "pin": "positive", "angle": 0,
    }
    holes = _holes(
        {"components": components, "nets": nets},
        "buzzer1",
        pins=["positive", "negative"],
    )
    assert holes == {"positive": "25e", "negative": "30e"}


def test_r12_piezo_con_cursor_26_no_entra_y_queda_unplaced():
    components, nets = _led_blocks(4)
    components.append({"ref": "btnx", "type": "pushbutton"})  # ocupa 25
    components.append({"ref": "buzzer1", "type": "buzzer"})
    result = plan_layout({"components": components, "nets": nets})

    assert result["placements"]["btnx"]["at"] == "25f"
    assert "buzzer1" not in result["placements"]
    assert result["unplaced"] == ["buzzer1"]


def test_r12_piezo_es_segunda_pasada_aunque_se_declare_primero():
    # Si el piezo tomara el cursor antes que el boton, el boton caeria en
    # la columna 30 o quedaria sin lugar.
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "buzzer1", "type": "buzzer"},
            {"ref": "btn1", "type": "pushbutton"},
        ],
        "nets": [
            ["uno.D8", "buzzer1.positive"],
            ["buzzer1.negative", "uno.GND1"],
            ["uno.D2", "btn1.1"],
            ["btn1.2", "uno.GND1"],
        ],
    }
    result = plan_layout(fixture)
    assert result["placements"]["btn1"]["at"] == "1f"
    assert result["placements"]["buzzer1"]["at"] == "24e"
    assert result["unplaced"] == []


# --------------------------------------------------------- layout: LDR

def _ldr_fixture(cursor_target, divider=True):
    """3 bloques LED (cursor 19) + botones hasta el cursor pedido."""
    components, nets = _led_blocks(3)
    for i in range(cursor_target - 19):
        components.append({"ref": f"btn{i}", "type": "pushbutton"})
    components.append({"ref": "ldr1", "type": "photoresistor"})
    if divider:
        components.append({"ref": "rdiv", "type": "resistor"})
        nets.append(["ldr1.2", "uno.A0", "rdiv.1"])
    else:
        nets.append(["ldr1.2", "uno.A0"])
    nets.append(["uno.5V", "ldr1.1"])
    return {"components": components, "nets": nets}


def test_r12_ldr_con_divisor_en_cursor_23_entra_completo():
    fixture = _ldr_fixture(23)
    result = plan_layout(fixture)
    assert result["unplaced"] == []
    assert result["placements"]["ldr1"] == {
        "at": "23e", "pin": "1", "angle": 0,
    }
    assert result["placements"]["rdiv"] == {
        "at": "26e", "pin": "1", "angle": 90,
    }
    # El bloque termina justo en la 30 y el builder puede rutearlo.
    assert _holes(fixture, "rdiv", pins=["1", "2"]) == {"1": "26e", "2": "30e"}
    assert fixture_to_model_call(fixture)


def test_r12_ldr_con_divisor_en_cursor_24_no_deja_media_colocacion():
    fixture = _ldr_fixture(24)
    result = plan_layout(fixture)
    assert "ldr1" not in result["placements"]
    assert "rdiv" not in result["placements"]
    assert result["unplaced"] == ["ldr1", "rdiv"]
    with pytest.raises(BuildError, match="ldr1"):
        fixture_to_model_call(fixture)


def test_r12_ldr_sin_divisor_en_cursor_23_ocupa_dos_columnas():
    fixture = _ldr_fixture(23, divider=False)
    result = plan_layout(fixture)
    assert result["unplaced"] == []
    assert result["placements"]["ldr1"]["at"] == "23e"
    assert _holes(fixture, "ldr1") == {"1": "23e", "2": "24e"}


def test_r12_ldr_con_dos_resistencias_en_el_nodo_medio_elige_la_primera():
    def fixture_with(net_order):
        return {
            "components": [
                {"ref": "uno", "type": "arduino-uno"},
                {"ref": "ldr1", "type": "photoresistor"},
                {"ref": "rA", "type": "resistor"},
                {"ref": "rB", "type": "resistor"},
            ],
            "nets": [
                ["ldr1.2", "uno.A0"] + [f"{ref}.1" for ref in net_order],
            ],
        }

    first = fixture_with(("rA", "rB"))
    result = plan_layout(first)
    assert result["unplaced"] == []
    # La divisora es la primera resistencia del nodo; la otra es bloque
    # independiente y no se come la columna del LDR.
    assert result["placements"]["rA"] == {"at": "25e", "pin": "1", "angle": 90}
    assert result["placements"]["rB"] == {"at": "1g", "pin": "1", "angle": 90}
    assert result["placements"]["ldr1"] == {"at": "22e", "pin": "1", "angle": 0}
    # Determinista: mismo dict de entrada, mismo resultado.
    assert plan_layout(copy.deepcopy(first)) == result

    second = plan_layout(fixture_with(("rB", "rA")))
    assert second["placements"]["rB"] == {"at": "25e", "pin": "1", "angle": 90}
    assert second["placements"]["rA"] == {"at": "1g", "pin": "1", "angle": 90}


def test_r12_ldr_no_roba_la_resistencia_serie_de_un_led():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "led1", "type": "led"},
            {"ref": "rled", "type": "resistor"},
            {"ref": "ldr1", "type": "photoresistor"},
            {"ref": "rdiv", "type": "resistor"},
        ],
        "nets": [
            ["rled.2", "led1.anode"],
            ["ldr1.2", "uno.A0", "rled.1", "rdiv.1"],
        ],
    }
    result = plan_layout(fixture)
    assert result["unplaced"] == []
    assert result["placements"]["rled"]["at"] == "1g"
    assert result["placements"]["rdiv"]["at"] == "25e"
    assert result["placements"]["ldr1"]["at"] == "22e"


def test_r12_piezo_y_ldr_juntos_solo_entra_uno_y_sin_media_colocacion():
    ldr_first = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "ldr1", "type": "photoresistor"},
            {"ref": "rdiv", "type": "resistor"},
            {"ref": "buzzer1", "type": "buzzer"},
        ],
        "nets": [
            ["ldr1.2", "uno.A0", "rdiv.1"],
            ["uno.D8", "buzzer1.positive"],
        ],
    }
    result = plan_layout(ldr_first)
    assert result["placements"]["ldr1"]["at"] == "22e"
    assert result["placements"]["rdiv"]["at"] == "25e"
    assert result["unplaced"] == ["buzzer1"]

    piezo_first = copy.deepcopy(ldr_first)
    piezo_first["components"] = [
        piezo_first["components"][0],
        piezo_first["components"][3],
        piezo_first["components"][1],
        piezo_first["components"][2],
    ]
    result = plan_layout(piezo_first)
    assert result["placements"]["buzzer1"]["at"] == "24e"
    assert set(result["unplaced"]) == {"ldr1", "rdiv"}
    assert len(result["placements"]) == 1


# ---------------------- regresion de orden: mismo circuito, mismos refs

def test_r12_ldr_divisor_no_cambia_la_fidelidad_al_reordenar_resistencias():
    """Mismo circuito fisico: solo cambia el ORDEN del array components.

    plan_layout empareja por nets y construye en el mismo orden, asi que
    el cableado emulado es identico. La fidelidad no puede depender de en
    que posicion del JSON se declaro cada resistencia.
    """
    fixture = _fixture("ldr-divisor")
    swapped = copy.deepcopy(fixture)
    components = swapped["components"]
    i1 = next(i for i, c in enumerate(components) if c["ref"] == "r1")
    i2 = next(i for i, c in enumerate(components) if c["ref"] == "r2")
    components[i1], components[i2] = components[i2], components[i1]

    def wire_tuples(inspect):
        return sorted(
            (
                w["source"]["instance_id"], w["source"]["pin"],
                w["target"]["instance_id"], w["target"]["pin"],
            )
            for w in inspect["wires"]
        )

    original = _emulate_inspect(fixture)
    reordered = _emulate_inspect(swapped)
    # Mismo Arduino, mismo breadboard y mismos partes/huecos.
    assert [c["type"] for c in original["components"]] == [
        c["type"] for c in reordered["components"]
    ]
    assert wire_tuples(original) == wire_tuples(reordered)
    original_fidelity = _fidelity(fixture)
    assert original_fidelity["score"] == 1.0
    reordered_fidelity = _fidelity(swapped)
    assert reordered_fidelity["score"] == 1.0, reordered_fidelity


# ------------------------------------------------------------ sketches

def test_r12_ldr_traza_y_write_son_la_misma_comparacion():
    sketch = ldr_led_sketch()
    match = re.search(
        r"int (\w+) = analogRead\((\w+)\);\s*"
        r"if \(\1 < (\d+)\) \{(.*?)\} else \{(.*?)\}",
        sketch,
        re.S,
    )
    assert match, sketch
    variable, analog, threshold, on_branch, off_branch = match.groups()
    assert analog == "A0"
    assert threshold == "300"
    assert f"digitalWrite(13, HIGH);" in on_branch
    assert 'Serial.println("TEST:LED=ON");' in on_branch
    assert f"digitalWrite(13, LOW);" in off_branch
    assert 'Serial.println("TEST:LED=OFF");' in off_branch
    # Borde luz == umbral: la comparacion es estricta, cae en OFF.
    assert "<=" not in match.group(0)
    # La traza de luz publica la MISMA variable que decide.
    assert f'Serial.print("TEST:LUZ=");' in sketch
    assert f"Serial.println({variable});" in sketch
    # No hay un segundo digitalWrite del LED fuera de las ramas.
    assert sketch.count("digitalWrite(13,") == 2


@pytest.mark.parametrize("threshold", [0, 300, 1023])
def test_r12_ldr_umbral_aparece_en_condicion_y_en_ambas_ramas(threshold):
    sketch = ldr_led_sketch(threshold=threshold)
    assert f"if (luz < {threshold}) {{" in sketch


@pytest.mark.parametrize("threshold", [-1, 1024, 300.5, True])
def test_r12_ldr_umbral_invalido_es_rechazado(threshold):
    with pytest.raises(ValueError):
        ldr_led_sketch(threshold=threshold)


def test_r12_ldr_pin_analogico_invalido_es_rechazado():
    with pytest.raises(ValueError):
        ldr_led_sketch(ldr_pin="D0")


def test_r12_parking_estado_servo_y_leds_en_las_mismas_ramas():
    sketch = parking_servo_sketch()
    match = re.search(
        r"int angulo;\s*if \(distancia < ([\d.]+)\) \{(.*?)\} else \{(.*?)\}\s*"
        r"servo\.write\(angulo\);",
        sketch,
        re.S,
    )
    assert match, sketch
    threshold, open_branch, closed_branch = match.groups()
    assert threshold == "130.0"
    assert "angulo = 90;" in open_branch
    assert "digitalWrite(11, HIGH);" in open_branch  # verde
    assert "digitalWrite(10, LOW);" in open_branch   # rojo apagado
    assert 'Serial.println("TEST:ESTADO=ABIERTO");' in open_branch
    assert "CERRADO" not in open_branch
    assert "angulo = 0;" in closed_branch
    assert "digitalWrite(10, HIGH);" in closed_branch  # rojo
    assert "digitalWrite(11, LOW);" in closed_branch
    assert 'Serial.println("TEST:ESTADO=CERRADO");' in closed_branch
    assert "ABIERTO" not in closed_branch
    # Solo una asignacion por rama: no hay angulo por defecto que enmascare.
    assert sketch.count("int angulo;") == 1
    assert sketch.count("angulo = 90;") == 1
    assert sketch.count("angulo = 0;") == 1
    # La traza del servo publica el mismo angulo que se escribe.
    assert 'Serial.print("TEST:SERVO=");' in sketch
    assert "Serial.println(angulo);" in sketch
    # Cada color se escribe en ambas ramas y solo uno queda en HIGH.
    for pin in (10, 11, 3):
        assert sketch.count(f"digitalWrite({pin},") == 2
    for pin in (10, 11):
        assert sketch.count(f"digitalWrite({pin}, HIGH)") == 1
        assert sketch.count(f"digitalWrite({pin}, LOW)") == 1
    assert "digitalWrite(3, HIGH)" not in sketch
    assert sketch.count("digitalWrite(3, LOW);") == 2


def test_r12_parking_mide_antes_de_escribir_y_publica_la_distancia():
    sketch = parking_servo_sketch()
    loop = sketch.split("void loop() {", 1)[1]
    i_pulse = loop.index("pulseIn(6, HIGH)")
    i_distance = loop.index("float distancia = duracion * 0.034 / 2;")
    i_trace = loop.index('Serial.print("TEST:DIST=");')
    i_branch = loop.index("if (distancia <")
    i_first_rgb = loop.index("digitalWrite(10,")
    assert i_pulse < i_distance < i_trace < i_branch < i_first_rgb


@pytest.mark.parametrize(
    "kwargs",
    [
        {"red": 11},
        {"green": 10},
        {"blue": 9},
        {"trig": 6},
        {"echo": 7},
        {"servo_pin": 6},
        {"servo_pin": 3},
    ],
)
def test_r12_parking_rechaza_pines_repetidos(kwargs):
    with pytest.raises(ValueError):
        parking_servo_sketch(**kwargs)


@pytest.mark.parametrize(
    "threshold, text",
    [(2, "2.0"), (2.0, "2.0"), (400, "400.0"), (400.0, "400.0"), (130, "130.0")],
)
def test_r12_parking_umbrales_borde_en_la_condicion(threshold, text):
    assert f"if (distancia < {text}) {{" in parking_servo_sketch(
        threshold_cm=threshold
    )


@pytest.mark.parametrize("threshold", [1.9, 1.99, 400.01, 401])
def test_r12_parking_umbrales_fuera_de_rango_son_rechazados(threshold):
    with pytest.raises(ValueError):
        parking_servo_sketch(threshold_cm=threshold)


def test_r12_parking_defaults_coinciden_con_la_fixture():
    sketch = parking_servo_sketch()
    for pin in (7, 6, 9, 10, 11, 3):
        assert f"pinMode({pin}," in sketch or f"servo.attach({pin})" in sketch
    assert "servo.attach(9);" in sketch
    assert "#include <Servo.h>" in sketch


def test_r12_buzzer_sketch_tone_y_noTone_en_ramas_opuestas():
    sketch = buzzer_button_sketch()
    match = re.search(
        r"if \(estado == LOW\) \{(.*?)\} else \{(.*?)\}",
        sketch,
        re.S,
    )
    assert match, sketch
    pressed, silent = match.groups()
    assert "tone(8, 880);" in pressed
    assert 'Serial.println("TEST:PRESSED");' in pressed
    assert "noTone(8);" not in pressed
    assert "noTone(8);" in silent
    assert 'Serial.println("TEST:SILENCIO");' in silent
    assert "pinMode(2, INPUT_PULLUP)" in sketch
    with pytest.raises(ValueError):
        buzzer_button_sketch(button_pin=8, buzzer_pin=8)
