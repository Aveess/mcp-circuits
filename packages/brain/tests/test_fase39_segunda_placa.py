"""Fase 39: el display de 7 segmentos deja de estallar y los cables se
reparten arriba/abajo.

Tres contratos, cada uno medido sobre el codigo real:

1. **Resistencia serie obligatoria.** Un segmento (o el anodo de un LED)
   colgado directo de un pin del Uno o de 5V/GND no se construye: en el
   simulador el display revienta aunque el conteo siga funcionando, asi que
   el oraculo no lo detecta. Si el otro extremo es una resistencia (o la
   salida de un integrado) la net pasa.
2. **Segunda protoboard.** ``"board2": [refs]`` manda esas resistencias a
   una segunda placa como banco vertical: angle 0, pin "1" en la fila d y
   pin "2" en la f (el cable del Uno entra por abajo y el del display sale
   por arriba). Los huecos viajan con prefijo ``b1/`` y el model call
   declara ``boards``.
3. **Nada a medias.** ``board2`` con una parte que no es resistencia, con
   refs inexistentes, repetidas o junto a ``free_parts`` falla con
   LayoutError antes de tocar Tinkercad.
"""

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from tinkercad_brain import sketches  # noqa: E402
from tinkercad_brain.builder import BuildError, fixture_to_model_call  # noqa: E402
from tinkercad_brain.layout import (  # noqa: E402
    SECOND_BOARD_COLUMN_STEP,
    SECOND_BOARD_FIRST_COLUMN,
    SECOND_BOARD_X,
    LayoutError,
    plan_layout,
)

FIXTURES = REPO / "fixtures" / "fase0" / "circuits.json"
NEW = "contador-555-compuertas"
SEGMENTS = "abcdefg"


def _fixture(fixture_id=NEW):
    fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))
    return next(f for f in fixtures if f["id"] == fixture_id)


def _pairs(call):
    return [(wire["from"], wire["to"]) for wire in call["wires"]]


# ------------------------------------------------- 1. resistencia serie


def test_un_segmento_directo_al_uno_no_se_construye():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "seg", "type": "seven-segment"},
        ],
        "nets": [["uno.D4", "seg.a"]],
    }
    with pytest.raises(BuildError) as error:
        fixture_to_model_call(fixture)
    assert "sin resistencia serie" in str(error.value)
    assert "seg.a" in str(error.value)


def test_un_led_directo_al_uno_no_se_construye():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "led1", "type": "led"},
        ],
        "nets": [["uno.D13", "led1.anode"]],
    }
    with pytest.raises(BuildError) as error:
        fixture_to_model_call(fixture)
    assert "led1.anode" in str(error.value)


def test_un_segmento_directo_a_5v_tampoco():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "seg", "type": "seven-segment"},
        ],
        "nets": [["uno.5V", "seg.a"]],
    }
    with pytest.raises(BuildError):
        fixture_to_model_call(fixture)


def test_el_catodo_de_un_led_no_es_la_pata_que_necesita_resistencia():
    """La resistencia puede ir en el anodo o despues del catodo: la net del
    catodo no se marca (LED y resistencia en serie, en cualquier orden)."""
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "led1", "type": "led"},
            {"ref": "r1", "type": "resistor"},
        ],
        "nets": [["uno.D13", "r1.1"], ["r1.2", "led1.anode"], ["led1.cathode", "uno.GND1"]],
    }
    call = fixture_to_model_call(fixture)
    assert call["wires"]


def test_un_segmento_por_integrado_pasa():
    """El 595 ya limita la corriente y es una topologia verificada."""
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "u1", "type": "shift-register"},
            {"ref": "seg", "type": "seven-segment"},
        ],
        "nets": [["u1.Q0", "seg.a"]],
    }
    call = fixture_to_model_call(fixture)
    assert any("seg.a" in (wire["from"], wire["to"]) for wire in call["wires"])


def test_la_fixture_nueva_tiene_las_siete_resistencias_de_segmento():
    fixture = _fixture()
    type_by_ref = {c["ref"]: c["type"] for c in fixture["components"]}
    nets = [set(net) for net in fixture["nets"]]

    def resistor_entre(a, b):
        for index, net in enumerate(nets):
            if a not in net:
                continue
            for endpoint in net:
                ref, _, pin = endpoint.partition(".")
                if type_by_ref.get(ref) == "resistor" and pin == "1":
                    return any(f"{ref}.2" in other and b in other for other in nets)
        return False

    for segment, pin in zip(SEGMENTS, (4, 5, 6, 7, 9, 10, 11)):
        assert resistor_entre(f"uno.D{pin}", f"seg.{segment}"), segment


# ------------------------------------------------- 2. segunda protoboard


def test_el_banco_vertical_va_en_la_segunda_placa():
    plan = plan_layout(_fixture())
    expected_cols = [
        SECOND_BOARD_FIRST_COLUMN + index * SECOND_BOARD_COLUMN_STEP
        for index in range(7)
    ]
    for index, column in enumerate(expected_cols):
        placement = plan["placements"][f"r{index + 2}"]
        assert placement["at"] == f"{column}d"
        assert placement["pin"] == "1"
        # Vertical: con angle 0 las patas quedan en la misma columna.
        assert placement["angle"] == 0
        assert placement["board"] == 1


def test_el_plan_declara_las_dos_placas():
    plan = plan_layout(_fixture())
    assert plan["boards"] == [{"x": 870, "y": 0}, {"x": SECOND_BOARD_X, "y": 0}]
    # Una fixture de una sola placa no agrega la clave: el puente ya coloca
    # la primera en (870, 0).
    assert "boards" not in plan_layout(_fixture("siete-segmentos"))


def test_el_model_call_prefija_los_huecos_y_declara_boards():
    call = fixture_to_model_call(_fixture())
    assert call["boards"] == [{"x": 870, "y": 0}, {"x": SECOND_BOARD_X, "y": 0}]
    parts = {part["ref"]: part for part in call["parts"]}
    assert [parts[f"r{i}"]["board"] for i in range(2, 9)] == [1] * 7
    pairs = _pairs(call)
    # Pin 1 (fila d) recibe el cable del Uno; pin 2 (fila f) va al display.
    for segment, pin, column in zip(
        SEGMENTS, (4, 5, 6, 7, 9, 10, 11), range(1, 26, SECOND_BOARD_COLUMN_STEP)
    ):
        assert (f"uno.D{pin}", f"b1/{column}d") in pairs, (segment, pairs)
        assert (f"b1/{column}f", f"seg.{segment}") in pairs, segment


def test_las_resistencias_del_banco_no_se_repiten_en_la_placa_1():
    """Cada resistencia tiene un solo placement: el banco, no ademas un
    bloque en la placa 1."""
    call = fixture_to_model_call(_fixture())
    refs = [part["ref"] for part in call["parts"]]
    for index in range(2, 9):
        assert refs.count(f"r{index}") == 1


def test_el_sketch_sigue_manejando_los_mismos_pines():
    """La resistencia serie cambia la corriente, no el pin ni la logica."""
    code = sketches.gate_counter_sketch()
    for pin in (4, 5, 6, 7, 9, 10, 11):
        assert f"{pin}" in code
    assert "digitalWrite(PINES[i], !DIGITOS[valor][i]);" in code


# ------------------------------------------------- 3. nada a medias


def test_board2_solo_acepta_resistencias():
    fixture = _fixture()
    fixture["board2"] = ["seg"]
    with pytest.raises(LayoutError) as error:
        plan_layout(fixture)
    assert "banco vertical de resistencias" in str(error.value)


def test_board2_con_ref_inexistente_falla():
    fixture = _fixture()
    fixture["board2"] = ["r99"]
    with pytest.raises(LayoutError) as error:
        plan_layout(fixture)
    assert "no existen" in str(error.value)


def test_board2_repetido_falla():
    fixture = _fixture()
    fixture["board2"] = ["r2", "r2"]
    with pytest.raises(LayoutError) as error:
        plan_layout(fixture)
    assert "repetida" in str(error.value)


def test_board2_no_comparte_lienzo_con_free_parts():
    fixture = _fixture()
    fixture["free_parts"] = ["sv1"]
    with pytest.raises(LayoutError) as error:
        plan_layout(fixture)
    assert "free_parts" in str(error.value)


# ------------------------------------------------- nets de alimentacion


def test_una_parte_de_la_placa_2_va_directa_al_uno_y_no_al_riel():
    """El tap del riel caeria en la placa 1: la parte de la placa 2 se
    cablea directo al pin del Uno."""
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "r1", "type": "resistor"},
            {"ref": "u1", "type": "shift-register"},
        ],
        # Una net de 5V con 3 extremos fuerza rieles; r1 vive en la placa 2
        # y el integrado sigue bajando al riel de la placa 1.
        "nets": [["uno.5V", "r1.1", "u1.Vcc"], ["u1.GND", "uno.GND1"]],
        "wiring": "rails",
        "board2": ["r1"],
    }
    call = fixture_to_model_call(fixture)
    pairs = _pairs(call)
    assert ("uno.5V", "b1/1d") in pairs, pairs
    assert any(to.startswith("T+") for frm, to in pairs if frm == "u1.Vcc"), pairs


def test_una_resistencia_del_banco_no_puede_ser_la_de_un_led():
    fixture = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "led1", "type": "led"},
            {"ref": "r1", "type": "resistor"},
        ],
        "nets": [["uno.D13", "r1.1"], ["r1.2", "led1.anode"], ["led1.cathode", "uno.GND1"]],
        "board2": ["r1"],
    }
    with pytest.raises(LayoutError) as error:
        plan_layout(fixture)
    assert "emparejadas" in str(error.value)


# ------------------------------------------------- identidad por nombre real


def _inspect_dos_resistencias(nombres):
    """"Inspect" minimo: dos resistencias y dos cables entre ellas."""
    components = [
        {"instance_id": "_1", "type": "Resistor", "name": nombres[0]},
        {"instance_id": "_2", "type": "Resistor", "name": nombres[1]},
    ]
    wires = [
        {"source": {"instance_id": "_1", "pin": "1"},
         "target": {"instance_id": "_2", "pin": "1"}},
        {"source": {"instance_id": "_1", "pin": "2"},
         "target": {"instance_id": "_2", "pin": "2"}},
    ]
    return {"components": components, "wires": wires}


def test_el_mapa_del_build_resuelve_los_nombres_deduplicados():
    """Tinkercad deja "r21" al pedir "r2" si el documento ya tenia "r2".

    El build devuelve el nombre real, y con el mapa las nets se leen con las
    refs de la fixture: sin el, "r21" se toma como una ref distinta y la
    conectividad no cuadra aunque el cableado sea perfecto.
    """
    from tinkercad_brain.breadboard_nets import derive_nets
    from tinkercad_brain.fase0.normalize import normalize_circuit

    inspect = _inspect_dos_resistencias(["r11", "r21"])
    refs_by_name = {"r11": "r1", "r21": "r2"}

    assert derive_nets(inspect, refs_by_name) == [
        ["r1.1", "r2.1"], ["r1.2", "r2.2"]
    ]
    normalized = normalize_circuit(inspect, {"nets": []}, refs_by_name)
    assert [c["ref"] for c in normalized["components"]] == ["r1", "r2"]


def test_sin_mapa_el_nombre_deduplicado_se_lee_como_otra_ref():
    """El nombre no alcanza: es el motivo de pasar el mapa del build.

    "r21" parece una ref valida (letra + digitos), asi que el criterio por
    nombre la acepta y produce nets que no casan con la fixture. El mapa
    nombre->ref es lo que devuelve la identidad real.
    """
    from tinkercad_brain.breadboard_nets import derive_nets

    inspect = _inspect_dos_resistencias(["r11", "r21"])
    assert derive_nets(inspect) == [["r11.1", "r21.1"], ["r11.2", "r21.2"]]


def test_el_runner_lee_los_nombres_del_resultado_del_build():
    import json as _json

    from tinkercad_brain.runner import _refs_by_name

    output = _json.dumps({
        "success": True,
        "placed": {
            "r2": {"angle": 0, "holes": {}, "name": "r21"},
            "r1": {"angle": 90, "holes": {}, "name": "r1"},
            "seg": {"angle": 0, "holes": {}, "free": {"x": 1, "y": 2}},
        },
    })
    assert _refs_by_name(output) == {"r21": "r2", "r1": "r1"}
    # Un puente viejo no manda nombres: mapa vacio y criterio anterior.
    assert _refs_by_name('{"success": true, "placed": {"r1": {"angle": 0}}}') == {}
    assert _refs_by_name("no json") == {}


# ------------------------------------------------- presets por ref


def test_los_presets_apuntan_a_refs_no_al_tipo():
    import demo_build as demo

    presets = demo.select_presets(_fixture())
    by_component = {preset["component"]: preset for preset in presets}
    assert by_component["r1"]["value"] == 68 and by_component["r1"]["unit"] == "k"
    assert by_component["c1"]["value"] == 10 and by_component["c1"]["unit"] == "u"
    for index in range(2, 9):
        assert by_component[f"r{index}"]["value"] == 220
    # Con siete resistencias mas la del 555, "Resistor" es ambiguo.
    assert "Resistor" not in by_component
