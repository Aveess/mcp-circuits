"""Tester independiente, ronda 2: normalize / report / component_map.

No repite los tests existentes: apunta a consistencia entre modulos
(normalize vs component_map vs fixtures reales), componentes duplicados,
entradas degeneradas y records no conformes. Un fallo aqui es un
hallazgo reportado, no un error del test.
"""

import json
from pathlib import Path

import pytest

from tinkercad_brain.fase0.component_map import TYPE_MAP, fixture_type, known_slugs
from tinkercad_brain.fase0.normalize import normalize_circuit
from tinkercad_brain.fase0.report import build_report

ROOT = Path(__file__).resolve().parents[1]
REAL_FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"


def _fixture_types():
    circuits = json.loads(REAL_FIXTURES.read_text(encoding="utf-8"))
    return {c["type"] for circuit in circuits for c in circuit["components"]}


def _normalized_type(ezhil_name):
    out = normalize_circuit(
        {"components": [{"type": ezhil_name, "instance_id": "x1"}]}, {"nets": []}
    )
    if ezhil_name == "Breadboard Small":
        # Ruling: el protoboard es infraestructura; ya no sale en components.
        assert out["components"] == []
        return "breadboard"
    return out["components"][0]["type"]


# ------------------------------------------------------- consistencia


def test_r2_basicos_normalize_coincide_con_mapa_y_fixtures():
    fixture_types = _fixture_types()
    for name in ("Arduino Uno R3", "LED", "Resistor"):
        assert _normalized_type(name) == fixture_type(name)
        assert _normalized_type(name) in fixture_types
        assert _normalized_type(name) in known_slugs()


@pytest.mark.parametrize("ezhil_name", sorted(TYPE_MAP))
def test_r2_todo_nombre_del_mapa_normaliza_a_su_slug_canonico(ezhil_name):
    # normalize tiene su propio _TYPE_MAP de solo 3 entradas: el resto
    # cae al slug mecanico, que no siempre es el slug de component_map.
    assert _normalized_type(ezhil_name) == TYPE_MAP[ezhil_name]


def test_r2_ultrasonico_normalizado_existe_en_fixtures_reales():
    # Mapa: "ultrasonic". Fixtures: "ultrasonic-hcsr04". Normalize: otro.
    assert _normalized_type("Ultrasonic Distance Sensor") in _fixture_types()


def test_r2_rgb_normalizado_existe_en_fixtures_reales():
    # Mapa y normalize: "rgb-led". Fixtures: "led-rgb-common-cathode".
    assert _normalized_type("RGB LED") in _fixture_types()


# ---------------------------------------------------------- normalize


def test_r2_dos_leds_por_instance_id_reciben_refs_distintas_en_nets():
    inspect_data = {
        "components": [
            {"type": "Arduino Uno R3", "instance_id": "uno_1"},
            {"type": "LED", "instance_id": "led_a"},
            {"type": "LED", "instance_id": "led_b"},
        ]
    }
    schematic_data = {
        "nets": [
            {"pins": [{"component": "led_a", "pin": "anode"},
                      {"component": "uno_1", "pin": "D13"}]},
            {"pins": [{"component": "led_b", "pin": "anode"},
                      {"component": "uno_1", "pin": "D12"}]},
        ]
    }
    out = normalize_circuit(inspect_data, schematic_data)
    assert out["nets"] == [["led1.anode", "uno.D13"], ["led2.anode", "uno.D12"]]


def test_r2_dos_leds_por_nombre_de_tipo_no_colapsan_ambos_a_led1():
    # El formato de schematic de los tests existentes referencia por
    # nombre de tipo ("LED"). Con dos LEDs, ambos nets no pueden
    # pertenecer a led1 dejando led2 huerfano.
    inspect_data = {
        "components": [
            {"type": "Arduino Uno R3", "instance_id": "uno_1"},
            {"type": "LED", "instance_id": "led_a"},
            {"type": "LED", "instance_id": "led_b"},
        ]
    }
    schematic_data = {
        "nets": [
            {"pins": [{"component": "LED", "pin": "anode"},
                      {"component": "Arduino Uno R3", "pin": "D13"}]},
            {"pins": [{"component": "LED", "pin": "anode"},
                      {"component": "Arduino Uno R3", "pin": "D12"}]},
        ]
    }
    out = normalize_circuit(inspect_data, schematic_data)
    refs_en_nets = {ep.partition(".")[0] for net in out["nets"] for ep in net}
    assert {"led1", "led2"} <= refs_en_nets


def test_r2_componente_sin_ninguna_net_se_conserva_y_no_inventa_nets():
    inspect_data = {
        "components": [
            {"type": "Arduino Uno R3", "instance_id": "uno_1"},
            {"type": "LED", "instance_id": "led_suelto"},
        ]
    }
    out = normalize_circuit(inspect_data, {"nets": []})
    assert out["components"] == [
        {"ref": "uno", "type": "arduino-uno"},
        {"ref": "led1", "type": "led"},
    ]
    assert out["nets"] == []


def test_r2_nets_vacias_y_pines_sin_componente_no_generan_endpoints():
    inspect_data = {"components": [{"type": "LED", "instance_id": "led_a"}]}
    schematic_data = {
        "nets": [
            [],
            {"pins": []},
            {"pins": [{}, {"pin": "anode"}, {"component": None, "pin": "x"}]},
            {"pins": [{"component": "led_a", "pin": "anode"}]},
        ]
    }
    assert normalize_circuit(inspect_data, schematic_data)["nets"] == []


def test_r2_pin_sin_nombre_no_crea_endpoint_none():
    inspect_data = {
        "components": [
            {"type": "Arduino Uno R3", "instance_id": "uno_1"},
            {"type": "LED", "instance_id": "led_a"},
        ]
    }
    schematic_data = {
        "nets": [
            {"pins": [{"component": "led_a"}, {"component": "uno_1", "pin": "D13"}]}
        ]
    }
    out = normalize_circuit(inspect_data, schematic_data)
    endpoints = [ep for net in out["nets"] for ep in net]
    assert not any(ep.endswith(".None") for ep in endpoints)


def test_r2_componente_sin_tipo_no_emite_tipo_vacio():
    out = normalize_circuit({"components": [{"instance_id": "x1"}]}, {"nets": []})
    assert all(comp["type"] for comp in out["components"])


# ------------------------------------------------------------- report


def test_r2_report_tool_repetido_mezcla_ok_y_fallo_agrega_todas_las_latencias():
    records = [
        {"tool": "probe", "ok": True, "elapsed_s": 1.0, "output": "a"},
        {"tool": "probe", "ok": False, "elapsed_s": 2.0, "output": "falla"},
        {"tool": "probe", "ok": True, "elapsed_s": 3.0, "output": "b"},
        {"tool": "probe", "ok": False, "elapsed_s": 100.0, "output": "falla2"},
    ]
    report = build_report(records)
    assert report["total_calls"] == 4
    assert [f["output"] for f in report["failures"]] == ["falla", "falla2"]
    assert report["latency"]["probe"]["n"] == 4
    assert report["latency"]["probe"]["worst"] == 100.0
    assert report["tools_used"] == ["probe"]


def test_r2_report_elapsed_negativo_es_rechazado_con_value_error():
    with pytest.raises(ValueError):
        build_report(
            [{"tool": "t", "ok": True, "elapsed_s": -0.5, "output": "x"}]
        )


def test_r2_report_output_entero_en_fallo_se_convierte_a_str():
    report = build_report(
        [{"tool": "t", "ok": False, "elapsed_s": 1.0, "output": 12345}]
    )
    assert report["failures"] == [{"tool": "t", "output": "12345"}]


def test_r2_report_output_lista_en_fallo_se_convierte_a_str():
    report = build_report(
        [{"tool": "t", "ok": False, "elapsed_s": 1.0, "output": ["boom"]}]
    )
    assert isinstance(report["failures"][0]["output"], str)


def test_r2_report_record_que_no_es_dict_falla_con_error_claro():
    with pytest.raises((TypeError, ValueError)):
        build_report(["no-soy-un-record"])


def test_r2_report_tool_ausente_mezclado_con_tool_nombrado_no_explota():
    report = build_report(
        [
            {"ok": True, "elapsed_s": 1.0, "output": "sin tool"},
            {"tool": "a", "ok": True, "elapsed_s": 1.0, "output": "ok"},
        ]
    )
    assert report["total_calls"] == 2


# ------------------------------------------------------- component_map


def test_r2_fixture_type_none_devuelve_none():
    assert fixture_type(None) is None


@pytest.mark.parametrize("weird", [123, 4.5])
def test_r2_fixture_type_no_string_devuelve_none(weird):
    assert fixture_type(weird) is None


def test_r2_fixture_type_solo_espacios_devuelve_none():
    assert fixture_type("   \t\n ") is None


def test_r2_type_map_no_tiene_slugs_duplicados():
    values = list(TYPE_MAP.values())
    assert len(values) == len(set(values))
    assert len(known_slugs()) == len(values)
