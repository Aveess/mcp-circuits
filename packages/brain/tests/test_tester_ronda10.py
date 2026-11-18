"""Tester independiente ronda 10: reutilizacion por titulo en run_build.

Fake propio sin tocar produccion. Contrato juzgado:
- La igualdad exacta (tras normalizar) debe ganar a la mera contencion,
  este donde este en la lista.
- Un match sin id utilizable no es reutilizable: se crea uno nuevo.
- Si abrir el circuito reutilizado falla, no se puede construir con
  clear_existing=True sobre lo que haya abierto: hay que caer a crear
  (mismo criterio que cuando la lista falla).
- clear_existing=True va solo en el build principal reutilizado; el
  repair solo recablea (parts vacias, sin clear).
"""
import json
from pathlib import Path

import pytest

from tinkercad_brain.builder import fixture_to_model_call
from tinkercad_brain.runner import run_build

ROOT = Path(__file__).resolve().parents[1]
REAL_FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"
CREATED = "created999"
CODE = "void setup() { pinMode(13, OUTPUT); }"


def _fixture():
    circuits = json.loads(REAL_FIXTURES.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == "blink-basico")


def _ep(component, pin, instance_id):
    return {"component": component, "pin": pin, "instance_id": instance_id}


def _inspect(missing=False):
    uno = ("Arduino Uno R3", "uno1")
    r = ("Resistor", "r_a")
    led = ("LED", "led_a")

    def comp(type_, instance_id):
        return {"type": type_, "instance_id": instance_id, "name": "1", "pins": []}

    def e(c, pin):
        return _ep(c[0], pin, c[1])

    wires = [
        {"source": e(uno, "D13"), "target": e(r, "Terminal 1")},
        {"source": e(r, "Terminal 2"), "target": e(led, "Anode")},
        {"source": e(led, "Cathode"), "target": e(uno, "GND")},
    ]
    if missing:
        wires = wires[:-1]
    return {"components": [comp(*uno), comp(*r), comp(*led)], "wires": wires}


def _fake(list_raw=None, inspect_sequence=None, open_mode="ok"):
    """open_mode: ok | raise_first | success_false_first (solo 1er open)."""
    calls = []
    state = {"inspect": 0, "open": 0}

    def call_tool(tool, arguments):
        calls.append((tool, arguments))
        if tool == "tinkercad_list_circuits":
            if list_raw is not None:
                return list_raw
            return json.dumps({"circuits": []})
        if tool == "tinkercad_create_circuit":
            return json.dumps({"circuit_id": CREATED})
        if tool == "tinkercad_open_circuit":
            state["open"] += 1
            if state["open"] == 1 and open_mode == "raise_first":
                raise RuntimeError("open exploto")
            if state["open"] == 1 and open_mode == "success_false_first":
                return json.dumps({"success": False, "error": "no abre"})
            return json.dumps({"success": True})
        if tool == "tinkercad_build_circuit_model":
            return json.dumps({"success": True, "persisted": True})
        if tool == "tinkercad_inspect_circuit":
            if inspect_sequence:
                idx = min(state["inspect"], len(inspect_sequence) - 1)
                state["inspect"] += 1
                return json.dumps(inspect_sequence[idx])
            return json.dumps(_inspect())
        if tool == "tinkercad_read_serial_monitor":
            return "blink: 1\n"
        return json.dumps({"success": True})

    call_tool.calls = calls
    return call_tool


def _tools(call_tool):
    return [t for t, _ in call_tool.calls]


def _builds(call_tool):
    return [a for t, a in call_tool.calls if t == "tinkercad_build_circuit_model"]


def _opens(call_tool):
    return [a for t, a in call_tool.calls if t == "tinkercad_open_circuit"]


def _list_raw(circuits):
    return json.dumps({"circuits": circuits})


# ------------------------------------------- exacto gana a contencion

def test_r10_exacto_gana_a_dos_contenidos_anteriores_titulo_corto():
    call_tool = _fake(list_raw=_list_raw([
        {"title": "blink-basico", "id": "contenido-basico"},
        {"title": "superblink-pro", "id": "contenido-super"},
        {"title": "blink", "id": "exacto-id"},
    ]))
    result = run_build(_fixture(), CODE, call_tool, "blink")
    assert result["reused"] is True
    assert result["circuit_id"] == "exacto-id"
    assert _opens(call_tool)[0] == {"circuit_id_or_url": "exacto-id"}
    assert "tinkercad_create_circuit" not in _tools(call_tool)


def test_r10_exacto_normalizado_al_final_gana_a_contenido_mas_largo():
    call_tool = _fake(list_raw=_list_raw([
        {"title": "Blink Runner Pro Max", "id": "contenido-largo"},
        {"title": "otro", "id": "zzz"},
        {"title": "blink_runner", "id": "exacto-norm"},
    ]))
    result = run_build(_fixture(), CODE, call_tool, "Blink Runner")
    assert result["circuit_id"] == "exacto-norm"
    assert result["reused"] is True
    assert "tinkercad_create_circuit" not in _tools(call_tool)


def test_r10_exacto_sin_id_no_tapa_pero_exacto_con_id_gana_a_contenido_con_id():
    call_tool = _fake(list_raw=_list_raw([
        {"title": "blink", "id": "   "},
        {"title": "blink-basico", "id": "contenido-con-id"},
        {"title": "BLINK", "id": "exacto-con-id"},
    ]))
    result = run_build(_fixture(), CODE, call_tool, "blink")
    assert result["circuit_id"] == "exacto-con-id"
    assert result["reused"] is True


def test_r10_sin_exacto_el_primer_contenido_es_el_reutilizado():
    # Sin exacto, la contencion es el mecanismo del slug en vivo
    # (p.ej. "existing42-blink-runner"): se documenta el primero.
    call_tool = _fake(list_raw=_list_raw([
        {"title": "blink-basico", "id": "primero"},
        {"title": "superblink-pro", "id": "segundo"},
    ]))
    result = run_build(_fixture(), CODE, call_tool, "blink")
    assert result["circuit_id"] == "primero"
    assert result["reused"] is True


# ------------------------------------------------- entradas malformadas

def test_r10_entradas_sin_titulo_sin_id_o_no_dict_no_rompen_ni_tapan_valida():
    call_tool = _fake(list_raw=_list_raw([
        "basura",
        42,
        {"id": "sin-titulo"},
        {"title": None, "id": "titulo-none"},
        {"title": "", "id": "titulo-vacio"},
        {"title": "Blink runner"},
        {"title": "Blink runner", "id": ""},
        {"title": "Blink runner", "id": "valido-final"},
    ]))
    result = run_build(_fixture(), CODE, call_tool, "Blink runner")
    assert result["reused"] is True
    assert result["circuit_id"] == "valido-final"
    assert result["ok"] is True
    assert "tinkercad_create_circuit" not in _tools(call_tool)


def test_r10_lista_json_en_raiz_en_vez_de_dict_tambien_reutiliza():
    call_tool = _fake(list_raw=json.dumps([
        {"title": "otro", "id": "zzz"},
        {"title": "Blink runner", "id": "desde-lista"},
    ]))
    result = run_build(_fixture(), CODE, call_tool, "Blink runner")
    assert result["reused"] is True
    assert result["circuit_id"] == "desde-lista"
    assert "tinkercad_create_circuit" not in _tools(call_tool)


def test_r10_match_sin_ningun_id_utilizable_cae_a_crear_sin_clear():
    call_tool = _fake(list_raw=_list_raw([
        {"title": "Blink runner"},
        {"title": "Blink runner", "id": "  ", "url": "https://example.com/sin-things"},
    ]))
    result = run_build(_fixture(), CODE, call_tool, "Blink runner")
    assert result["reused"] is False
    assert result["circuit_id"] == CREATED
    assert "tinkercad_create_circuit" in _tools(call_tool)
    assert _builds(call_tool)[0]["clear_existing"] is False


def test_r10_id_desde_url_things_o_entero_es_utilizable():
    for entry, expected in (
        ({"title": "Blink runner", "url": "https://www.tinkercad.com/things/urlid77/editel"}, "urlid77"),
        ({"title": "Blink runner", "id": 12345}, "12345"),
    ):
        call_tool = _fake(list_raw=_list_raw([entry]))
        result = run_build(_fixture(), CODE, call_tool, "Blink runner")
        assert result["reused"] is True, entry
        assert result["circuit_id"] == expected, entry
        assert "tinkercad_create_circuit" not in _tools(call_tool)


def test_r10_circuits_no_lista_cae_a_crear():
    call_tool = _fake(list_raw=json.dumps({"circuits": {"title": "Blink runner", "id": "x"}}))
    result = run_build(_fixture(), CODE, call_tool, "Blink runner")
    assert result["reused"] is False
    assert result["circuit_id"] == CREATED


def test_r10_buscado_mas_largo_que_el_devuelto_no_es_match():
    # Solo vale buscado contenido en devuelto, no al reves.
    call_tool = _fake(list_raw=_list_raw([{"title": "Blink runner", "id": "corto"}]))
    result = run_build(_fixture(), CODE, call_tool, "Blink runner pro")
    assert result["reused"] is False
    assert result["circuit_id"] == CREATED


@pytest.mark.parametrize("returned", [
    "BLINK-RUNNER", "blink_runner", "  Blink   Runner  ", "blinkrunner", "Blink runner",
])
def test_r10_normalizacion_exacta_variantes(returned):
    call_tool = _fake(list_raw=_list_raw([{"title": returned, "id": "norm-id"}]))
    result = run_build(_fixture(), CODE, call_tool, "Blink Runner")
    assert result["reused"] is True
    assert result["circuit_id"] == "norm-id"


# ------------------------------------------------------- open que falla

def test_r10_open_reutilizado_excepcion_no_construye_sobre_reusado_cae_a_crear():
    call_tool = _fake(
        list_raw=_list_raw([{"title": "Blink runner", "id": "existente1"}]),
        open_mode="raise_first",
    )
    result = run_build(_fixture(), CODE, call_tool, "Blink runner")
    # No crear tras un open fallido dejaria el build (con clear) actuando
    # sobre cualquier circuito que quedara abierto.
    assert "tinkercad_create_circuit" in _tools(call_tool)
    assert result["reused"] is False
    assert result["circuit_id"] == CREATED
    assert _builds(call_tool)[0]["clear_existing"] is False
    open_records = [r for r in result["records"] if r.tool == "tinkercad_open_circuit"]
    assert open_records[0].ok is False


def test_r10_open_reutilizado_success_false_no_construye_sobre_reusado_cae_a_crear():
    call_tool = _fake(
        list_raw=_list_raw([{"title": "Blink runner", "id": "existente1"}]),
        open_mode="success_false_first",
    )
    result = run_build(_fixture(), CODE, call_tool, "Blink runner")
    assert "tinkercad_create_circuit" in _tools(call_tool)
    assert result["reused"] is False
    assert result["circuit_id"] == CREATED
    assert _builds(call_tool)[0]["clear_existing"] is False


# ------------------------------------------- clear solo en build principal

def test_r10_reuse_nunca_crea_y_repair_sin_clear_ni_parts():
    fixture = _fixture()
    call_tool = _fake(
        list_raw=_list_raw([{"title": "Blink runner", "id": "existente1"}]),
        inspect_sequence=[_inspect(missing=True), _inspect()],
    )
    result = run_build(fixture, CODE, call_tool, "Blink runner")
    assert result["reused"] is True
    assert result["repair_attempted"] is True
    assert result["ok"] is True
    assert "tinkercad_create_circuit" not in _tools(call_tool)
    builds = _builds(call_tool)
    assert len(builds) == 2
    assert builds[0] == {**fixture_to_model_call(fixture), "clear_existing": True}
    # El repair solo recablea: si llevara clear_existing=True borraria
    # las parts recien puestas antes de recablear.
    assert builds[1] == {"parts": [], "wires": fixture_to_model_call(fixture)["wires"]}
    assert builds[1].get("clear_existing") is not True
