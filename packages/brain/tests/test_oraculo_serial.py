"""El oráculo del serial como contrato, no como lectura humana.

Hoy `ok` no mira el serial: un circuito cuyo sketch imprime `TEST:ON` /
`TEST:OFF` puede reportar `OK: True` con **0 líneas** capturadas y nadie se
entera. El serial es la única prueba de comportamiento que tenemos, así que
tiene que estar en la puerta de `ok`:

- Si la fixture declara `oracle_serial`, cada marca debe aparecer **en ese
  orden** en la salida.
- Si no la declara pero el sketch usa `Serial`, la salida no puede venir
  vacía: "no imprimió nada" no es "funcionó".
"""

from __future__ import annotations

import json

from tinkercad_brain.oracle import check_serial

FIXTURE = {
    "id": "blink",
    "title": "Blink",
    "components": [{"ref": "uno", "type": "arduino-uno"}],
    "nets": [],
    "oracle_serial": ["TEST:ON", "TEST:OFF"],
}

CODE = 'void setup() { Serial.begin(9600); }\nvoid loop() { Serial.println("TEST:ON"); }'


class TestCheckSerial:
    def test_sin_expectativas_no_hay_nada_que_fallar(self):
        res = check_serial("cualquier cosa", [])
        assert res == {"ok": True, "missing": [], "found": []}

    def test_las_marcas_aparecen_en_orden(self):
        serial = "READY\nTEST:ON\nTEST:OFF\nTEST:ON\n"
        res = check_serial(serial, ["TEST:ON", "TEST:OFF"])
        assert res["ok"] is True
        assert res["missing"] == []
        assert res["found"] == ["TEST:ON", "TEST:OFF"]

    def test_una_marca_que_falta_se_nombra(self):
        res = check_serial("READY\nTEST:ON\n", ["TEST:ON", "TEST:OFF"])
        assert res["ok"] is False
        assert res["missing"] == ["TEST:OFF"]
        assert res["found"] == ["TEST:ON"]

    def test_el_orden_importa(self):
        res = check_serial("TEST:OFF\nTEST:ON\n", ["TEST:ON", "TEST:OFF"])
        assert res["ok"] is False
        assert res["missing"] == ["TEST:OFF"]

    def test_no_se_confunde_el_prefijo_con_la_marca(self):
        """`TEST:LED=OFF` no satisface `TEST:LED=ON`, ni al revés."""
        res = check_serial("TEST:LED=OFF\n", ["TEST:LED=ON"])
        assert res["ok"] is False
        assert res["missing"] == ["TEST:LED=ON"]

    def test_una_marca_repetida_se_puede_pedir_dos_veces(self):
        res = check_serial("TEST:ON\nTEST:OFF\nTEST:ON\n", ["TEST:ON", "TEST:OFF", "TEST:ON"])
        assert res["ok"] is True


def _call_tool(serial, inspect_vacio=False):
    from tests.test_runner_lectura import _inspect_blink

    def call_tool(tool, arguments):
        if tool == "tinkercad_inspect_circuit":
            return json.dumps(
                {"success": True, "components": [], "wires": []}
                if inspect_vacio
                else _inspect_blink()
            )
        if tool == "tinkercad_build_circuit_model":
            return json.dumps({"success": True, "persisted": True, "routed": 1, "route_debug": []})
        if tool == "tinkercad_read_serial_monitor":
            return serial
        return json.dumps({"success": True})

    return call_tool


def _run(fixture, serial, code="void setup(){}", **kwargs):
    from tinkercad_brain.runner import run_build

    return run_build(fixture, code, _call_tool(serial), "Oracle", preferred_id="abc123", **kwargs)


def test_un_oraculo_cumplido_deja_ok_true():
    fixture = dict(FIXTURE, components=[{"ref": "uno", "type": "arduino-uno"},
                                        {"ref": "r1", "type": "resistor"},
                                        {"ref": "led1", "type": "led"}],
                   nets=[["uno.D13", "r1.1"], ["r1.2", "led1.anode"], ["led1.cathode", "uno.GND"]])
    result = _run(fixture, "READY\nTEST:ON\nTEST:OFF\n", code=CODE)
    assert result["checks"]["oracle_ok"] is True
    assert result["checks"]["oracle_missing"] == []
    assert result["ok"] is True


def test_un_oraculo_incumplido_tumba_el_ok_aunque_la_fidelidad_sea_100():
    fixture = dict(FIXTURE, components=[{"ref": "uno", "type": "arduino-uno"},
                                        {"ref": "r1", "type": "resistor"},
                                        {"ref": "led1", "type": "led"}],
                   nets=[["uno.D13", "r1.1"], ["r1.2", "led1.anode"], ["led1.cathode", "uno.GND"]])
    result = _run(fixture, "READY\nTEST:ON\n", code=CODE)
    assert result["fidelity"]["score"] == 1.0
    assert result["checks"]["oracle_ok"] is False
    assert result["checks"]["oracle_missing"] == ["TEST:OFF"]
    assert result["ok"] is False


def test_un_sketch_que_imprime_no_puede_dejar_el_serial_vacio():
    """Cero líneas no es "funcionó": es una prueba que falta."""
    fixture = dict(FIXTURE)
    fixture.pop("oracle_serial")
    fixture["components"] = [{"ref": "uno", "type": "arduino-uno"},
                             {"ref": "r1", "type": "resistor"},
                             {"ref": "led1", "type": "led"}]
    fixture["nets"] = [["uno.D13", "r1.1"], ["r1.2", "led1.anode"], ["led1.cathode", "uno.GND"]]
    result = _run(fixture, "", code=CODE)
    assert result["checks"]["serial_nonempty"] is False
    assert result["checks"]["oracle_ok"] is True  # no hay marcas declaradas
    assert result["ok"] is False


def test_si_el_sketch_no_usa_serial_ni_se_declara_oraculo_no_se_exige_nada():
    fixture = {"id": "mudo", "title": "Mudo",
               "components": [{"ref": "uno", "type": "arduino-uno"},
                              {"ref": "r1", "type": "resistor"},
                              {"ref": "led1", "type": "led"}],
               "nets": [["uno.D13", "r1.1"], ["r1.2", "led1.anode"],
                        ["led1.cathode", "uno.GND"]]}
    result = _run(fixture, "", code="void setup(){}")
    assert result["checks"]["serial_nonempty"] is True
    assert result["checks"]["oracle_ok"] is True
    assert result["ok"] is True


def test_el_reporte_nombra_la_marca_que_falto():
    from tinkercad_brain.documenter import render_build_report

    reporte = render_build_report(
        "Blink",
        "https://www.tinkercad.com/things/abc123/editel",
        {"score": 1.0, "components_score": 1.0, "nets_score": 1.0},
        "TEST:ON",
        [],
        oracle={
            "expected": ["TEST:ON", "TEST:OFF"],
            "found": ["TEST:ON"],
            "missing": ["TEST:OFF"],
            "ok": False,
            "serial_required": True,
            "serial_lines": 1,
        },
    )
    assert "## Oráculo" in reporte
    assert "`TEST:OFF`" in reporte
    assert "oráculo: falta" in reporte


def test_el_reporte_no_dice_sin_fallos_si_el_oraculo_fallo():
    from tinkercad_brain.documenter import render_build_report

    reporte = render_build_report(
        "Blink",
        "https://www.tinkercad.com/things/abc123/editel",
        {"score": 1.0},
        "sin serial",
        [],
        oracle={
            "expected": [],
            "found": [],
            "missing": [],
            "ok": True,
            "serial_required": True,
            "serial_lines": 0,
        },
    )
    assert "serial: el sketch imprime y no se capturó ninguna línea" in reporte
    assert "Sin fallos." not in reporte


def test_el_contrato_viaja_dentro_del_circuito_documentado():
    from tinkercad_brain.circuit_doc import render_circuit_doc

    fixture = {
        "id": "blink",
        "title": "Blink",
        "components": [{"ref": "uno", "type": "arduino-uno"}],
        "nets": [],
        "oracle_serial": ["TEST:ON", "TEST:OFF"],
    }
    doc = "\n".join(render_circuit_doc(fixture))
    assert "El serial debe imprimir, en orden: TEST:ON, TEST:OFF." in doc
