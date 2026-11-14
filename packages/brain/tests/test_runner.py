import json
from pathlib import Path

from tinkercad_brain.builder import fixture_to_model_call
from tinkercad_brain.fase0.probe import ProbeRecord
from tinkercad_brain.runner import run_build

ROOT = Path(__file__).resolve().parents[1]
REAL_FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"
CIRCUIT_ID = "abc123XYZ"
CODE = "void setup() { pinMode(13, OUTPUT); }"


def _fixture(fixture_id="blink-basico"):
    circuits = json.loads(REAL_FIXTURES.read_text(encoding="utf-8"))
    return next(c for c in circuits if c["id"] == fixture_id)


def _ep(component, pin, instance_id):
    return {"component": component, "pin": pin, "instance_id": instance_id}


def _inspect_blink():
    """Inspect con wires directos (sin protoboard) coherente con blink-basico."""
    uno = ("Arduino Uno R3", "uno1")
    r = ("Resistor", "r_a")
    led = ("LED", "led_a")

    def comp(type_, instance_id):
        return {"type": type_, "instance_id": instance_id, "name": "1", "pins": []}

    def wire(source, target):
        return {"source": source, "target": target}

    def e(component, pin):
        return _ep(component[0], pin, component[1])

    return {
        "components": [comp(*uno), comp(*r), comp(*led)],
        "wires": [
            wire(e(uno, "D13"), e(r, "Terminal 1")),
            wire(e(r, "Terminal 2"), e(led, "Anode")),
            wire(e(led, "Cathode"), e(uno, "GND")),
        ],
    }


def _inspect_blink_missing():
    data = _inspect_blink()
    data["wires"] = data["wires"][:-1]
    return data


def _inspect_blink_short():
    data = _inspect_blink()
    data["wires"].append(
        {
            "source": _ep("Arduino Uno R3", "D13", "uno1"),
            "target": _ep("Arduino Uno R3", "GND", "uno1"),
        }
    )
    return data


def _fake_call_tool(
    build_output=None,
    create_output=None,
    serial_output="blink: 1\n",
    inspect_sequence=None,
    fail_preset=False,
    list_output=None,
    fail_list=False,
):
    calls = []
    state = {"inspect": 0}

    def call_tool(tool, arguments):
        calls.append((tool, arguments))
        if tool == "tinkercad_list_circuits":
            if fail_list:
                raise RuntimeError("list exploto")
            if list_output is not None:
                return list_output
            return json.dumps({"circuits": []})
        if tool == "tinkercad_create_circuit":
            if create_output is not None:
                return create_output
            return json.dumps({"circuit_id": CIRCUIT_ID})
        if tool == "tinkercad_build_circuit_model":
            if build_output is not None:
                return build_output
            return json.dumps({"success": True, "persisted": True})
        if tool == "tinkercad_set_component_property_model" and fail_preset:
            raise RuntimeError("tool no existe: tinkercad_set_component_property_model")
        if tool == "tinkercad_inspect_circuit":
            if inspect_sequence:
                index = min(state["inspect"], len(inspect_sequence) - 1)
                state["inspect"] += 1
                return json.dumps(inspect_sequence[index])
            return json.dumps(_inspect_blink())
        if tool == "tinkercad_read_serial_monitor":
            return serial_output
        return json.dumps({"success": True})

    call_tool.calls = calls
    return call_tool


def test_happy_path_ok_true_full_order_and_serial():
    fixture = _fixture()
    call_tool = _fake_call_tool(serial_output="blink: 1\nblink: 2\n")

    result = run_build(fixture, CODE, call_tool, "Blink runner")

    tools = [tool for tool, _ in call_tool.calls]
    assert tools == [
        "tinkercad_list_circuits",
        "tinkercad_create_circuit",
        "tinkercad_build_circuit_model",
        "tinkercad_set_code",
        "tinkercad_open_circuit",
        "tinkercad_inspect_circuit",
        "tinkercad_start_simulation",
        "tinkercad_read_serial_monitor",
        "tinkercad_stop_simulation",
    ]
    assert call_tool.calls[1][1] == {"title": "Blink runner"}
    assert call_tool.calls[2][1] == {
        **fixture_to_model_call(fixture),
        "clear_existing": False,
    }
    assert call_tool.calls[3][1] == {"code": CODE}
    assert call_tool.calls[4][1] == {"circuit_id_or_url": CIRCUIT_ID}
    assert call_tool.calls[6][1] == {"wait_seconds": 5}
    assert result["reused"] is False

    assert result["circuit_id"] == CIRCUIT_ID
    assert result["url"] == f"https://www.tinkercad.com/things/{CIRCUIT_ID}/editel"
    assert result["fidelity"]["score"] == 1.0
    assert result["serial"] == "blink: 1\nblink: 2\n"
    assert result["ok"] is True
    assert [r.tool for r in result["records"]] == tools
    assert all(isinstance(r, ProbeRecord) for r in result["records"])
    assert all(r.ok for r in result["records"])


def test_un_tramo_horizontal_sobre_la_placa_tumba_el_ok():
    """100% de fidelidad no alcanza si un cable se ve pegado a la placa.

    La fidelidad compara conexiones, no geometria: el cable puede estar
    perfectamente conectado y pasar por encima del cuerpo (fase 40).
    """
    fixture = _fixture()
    pegado = json.dumps({
        "success": True,
        "persisted": True,
        "route_debug": [{
            "wire": "uno.D13 -> 5e",
            "routed": True,
            "reason": "ok",
            "points": [[200, 0], [200, 115], [765, 115], [765, 15]],
        }],
    })
    call_tool = _fake_call_tool(build_output=pegado)
    result = run_build(fixture, CODE, call_tool, "Con cable pegado")
    assert result["fidelity"]["score"] == 1.0
    assert result["route_violations"] == [
        {"wire": "uno.D13 -> 5e", "y": 115.0, "board": {"x": 870.0, "y": 0.0}}
    ]
    assert result["ok"] is False

    limpio = json.dumps({
        "success": True,
        "persisted": True,
        "route_debug": [{
            "wire": "uno.D13 -> 5e",
            "routed": True,
            "reason": "ok",
            "points": [[200, 0], [200, 130], [765, 130], [765, 15]],
        }],
    })
    result = run_build(fixture, CODE, _fake_call_tool(build_output=limpio), "Con cable limpio")
    assert result["route_violations"] == []
    assert result["ok"] is True


def test_no_code_skips_set_code():
    fixture = _fixture()
    call_tool = _fake_call_tool()

    result = run_build(fixture, None, call_tool, "Blink sin codigo")

    assert result["ok"] is True
    assert [tool for tool, _ in call_tool.calls] == [
        "tinkercad_list_circuits",
        "tinkercad_create_circuit",
        "tinkercad_build_circuit_model",
        "tinkercad_open_circuit",
        "tinkercad_inspect_circuit",
        "tinkercad_start_simulation",
        "tinkercad_read_serial_monitor",
        "tinkercad_stop_simulation",
    ]


def test_build_success_false_forces_ok_false_despite_fidelity():
    fixture = _fixture()
    call_tool = _fake_call_tool(
        build_output=json.dumps({"success": False, "error": "boom"})
    )

    result = run_build(fixture, CODE, call_tool, "Blink roto")

    assert result["fidelity"]["score"] == 1.0
    assert result["ok"] is False


def test_build_persisted_false_forces_ok_false_despite_fidelity():
    fixture = _fixture()
    call_tool = _fake_call_tool(
        build_output=json.dumps({"success": True, "persisted": False})
    )

    result = run_build(fixture, CODE, call_tool, "Blink sin persistir")

    assert result["fidelity"]["score"] == 1.0
    assert result["ok"] is False


def test_create_without_id_cuts_without_calling_rest():
    fixture = _fixture()
    call_tool = _fake_call_tool(create_output=json.dumps({"success": True}))

    result = run_build(fixture, CODE, call_tool, "Sin id")

    assert result["ok"] is False
    assert result["circuit_id"] == ""
    assert result["serial"] == ""
    assert result["reused"] is False
    assert [tool for tool, _ in call_tool.calls] == [
        "tinkercad_list_circuits",
        "tinkercad_create_circuit",
    ]
    assert len(result["records"]) == 2
    assert result["records"][1].tool == "tinkercad_create_circuit"


def test_happy_path_no_repair_when_score_already_perfect():
    fixture = _fixture()
    call_tool = _fake_call_tool()

    result = run_build(fixture, CODE, call_tool, "Sin reparacion")

    assert result["fidelity"]["score"] == 1.0
    assert result["repair_attempted"] is False
    builds = [c for c in call_tool.calls if c[0] == "tinkercad_build_circuit_model"]
    assert len(builds) == 1


def test_repair_recables_once_and_recovers_fidelity():
    fixture = _fixture()
    call_tool = _fake_call_tool(
        inspect_sequence=[_inspect_blink_missing(), _inspect_blink()]
    )

    result = run_build(fixture, CODE, call_tool, "Con reparacion")

    assert result["repair_attempted"] is True
    assert result["fidelity_before_repair"]["score"] < 0.99
    assert result["fidelity"]["score"] == 1.0
    assert result["ok"] is True
    builds = [c for c in call_tool.calls if c[0] == "tinkercad_build_circuit_model"]
    assert len(builds) == 2
    assert builds[1][1] == {
        "parts": [],
        "wires": fixture_to_model_call(fixture)["wires"],
    }
    tools = [tool for tool, _ in call_tool.calls]
    assert tools.count("tinkercad_open_circuit") == 2
    assert tools.count("tinkercad_inspect_circuit") == 2


def test_repair_disabled_does_not_retry():
    fixture = _fixture()
    call_tool = _fake_call_tool(
        inspect_sequence=[_inspect_blink_missing(), _inspect_blink()]
    )

    result = run_build(fixture, CODE, call_tool, "Sin repair", repair=False)

    assert result["repair_attempted"] is False
    assert result["fidelity"]["score"] < 0.99
    builds = [c for c in call_tool.calls if c[0] == "tinkercad_build_circuit_model"]
    assert len(builds) == 1


def test_shorts_do_not_trigger_repair():
    fixture = _fixture()
    call_tool = _fake_call_tool(inspect_sequence=[_inspect_blink_short()])

    result = run_build(fixture, CODE, call_tool, "Con corto")

    assert result["fidelity"]["shorts"]
    assert result["fidelity"]["score"] < 0.99
    assert result["repair_attempted"] is False
    builds = [c for c in call_tool.calls if c[0] == "tinkercad_build_circuit_model"]
    assert len(builds) == 1


def test_preset_applied_after_build_before_reopen():
    fixture = _fixture()
    call_tool = _fake_call_tool()
    presets = [{"component": "Comp X", "property": "Target Y", "value": -105}]

    result = run_build(fixture, CODE, call_tool, "Con preset", presets=presets)

    assert result["ok"] is True
    tools = [tool for tool, _ in call_tool.calls]
    preset_index = tools.index("tinkercad_set_component_property_model")
    assert tools.index("tinkercad_build_circuit_model") < preset_index
    assert preset_index < tools.index("tinkercad_open_circuit")
    assert call_tool.calls[preset_index][1] == {
        "component_name": "Comp X",
        "property_name": "Target Y",
        "value": -105,
    }


def test_preset_resuelve_el_nombre_real_que_dejo_el_editor():
    """Tinkercad deduplica el nombre: si dejo "r21", el preset va a "r21".

    Sin esto el preset se pierde con "component not found: r2" aunque el
    cableado y el layout esten bien (fase 39).
    """
    fixture = _fixture()
    build = json.dumps({
        "success": True,
        "persisted": True,
        "placed": {
            "r2": {"angle": 0, "holes": {}, "name": "r21"},
            "seg": {"angle": 0, "holes": {}, "free": {"x": 1, "y": 2}},
        },
    })
    call_tool = _fake_call_tool(build_output=build)
    presets = [
        {"component": "r2", "property": "resistance", "value": 220},
        {"component": "Resistor", "property": "resistance", "value": 10, "unit": "k"},
    ]

    run_build(fixture, CODE, call_tool, "Con nombres raros", presets=presets)

    names = [
        args["component_name"]
        for tool, args in call_tool.calls
        if tool == "tinkercad_set_component_property_model"
    ]
    # La ref se traduce al nombre real; un preset por tipo pasa tal cual.
    assert names == ["r21", "Resistor"]


def test_preset_failure_is_recorded_and_does_not_abort():
    fixture = _fixture()
    call_tool = _fake_call_tool(fail_preset=True)
    presets = [{"component": "Comp X", "property": "Target Y", "value": -105}]

    result = run_build(fixture, CODE, call_tool, "Preset roto", presets=presets)

    assert result["ok"] is True
    assert result["fidelity"]["score"] == 1.0
    preset_records = [
        r for r in result["records"] if r.tool == "tinkercad_set_component_property_model"
    ]
    assert len(preset_records) == 1
    assert preset_records[0].ok is False


def test_create_non_json_output_cuts_without_raising():
    fixture = _fixture()
    call_tool = _fake_call_tool(create_output="no-json-no-id")

    result = run_build(fixture, CODE, call_tool, "Sin json")

    assert result["ok"] is False
    assert [tool for tool, _ in call_tool.calls] == [
        "tinkercad_list_circuits",
        "tinkercad_create_circuit",
    ]
    assert len(result["records"]) == 2


def test_reuse_match_does_not_create_opens_existing_and_clears():
    fixture = _fixture()
    list_output = json.dumps(
        {
            "circuits": [
                {"title": "otro circuito", "id": "zzz999"},
                # slug en vivo: id prefijado + titulo con guiones
                {"title": "existing42-blink-runner", "id": "existing42"},
            ]
        }
    )
    call_tool = _fake_call_tool(list_output=list_output)

    result = run_build(fixture, CODE, call_tool, "Blink runner")

    tools = [tool for tool, _ in call_tool.calls]
    assert "tinkercad_create_circuit" not in tools
    assert result["reused"] is True
    assert result["circuit_id"] == "existing42"
    assert result["url"] == "https://www.tinkercad.com/things/existing42/editel"
    assert result["ok"] is True
    open_calls = [c for c in call_tool.calls if c[0] == "tinkercad_open_circuit"]
    assert open_calls[0][1] == {"circuit_id_or_url": "existing42"}
    assert tools.index("tinkercad_open_circuit") < tools.index(
        "tinkercad_build_circuit_model"
    )
    builds = [c for c in call_tool.calls if c[0] == "tinkercad_build_circuit_model"]
    assert builds[0][1] == {
        **fixture_to_model_call(fixture),
        "clear_existing": True,
    }


def test_tinkercad_id_clavado_reusa_por_id_sin_buscar_por_titulo():
    """Un diseno ya construido se reusa por id aunque el titulo no coincida.

    Con el match por titulo, renombrar el diseno en Tinkercad creaba un
    duplicado en el siguiente build (paso con motor-dc-transistor).
    """
    fixture = _fixture()
    list_output = json.dumps(
        {"circuits": [{"title": "otro circuito", "id": "zzz999"}]}
    )
    call_tool = _fake_call_tool(list_output=list_output)

    result = run_build(
        fixture, CODE, call_tool, "Blink runner", preferred_id="pinned77"
    )

    tools = [tool for tool, _ in call_tool.calls]
    assert "tinkercad_list_circuits" not in tools
    assert "tinkercad_create_circuit" not in tools
    assert result["reused"] is True
    assert result["circuit_id"] == "pinned77"
    open_calls = [c for c in call_tool.calls if c[0] == "tinkercad_open_circuit"]
    assert open_calls[0][1] == {"circuit_id_or_url": "pinned77"}
    builds = [c for c in call_tool.calls if c[0] == "tinkercad_build_circuit_model"]
    assert builds[0][1]["clear_existing"] is True


def test_tinkercad_id_clavado_que_ya_no_existe_cae_al_match_por_titulo():
    fixture = _fixture()
    list_output = json.dumps(
        {"circuits": [{"title": "existing42-blink-runner", "id": "existing42"}]}
    )

    def call_tool(tool, arguments):
        if tool == "tinkercad_open_circuit" and arguments.get("circuit_id_or_url") == "gone404":
            return json.dumps({"success": False, "message": "not found"})
        return _fake_call_tool(list_output=list_output)(tool, arguments)

    result = run_build(
        fixture, CODE, call_tool, "Blink runner", preferred_id="gone404"
    )

    assert result["reused"] is True
    assert result["circuit_id"] == "existing42"


def test_reuse_without_match_creates():
    fixture = _fixture()
    list_output = json.dumps(
        {"circuits": [{"title": "otro circuito", "id": "zzz999"}]}
    )
    call_tool = _fake_call_tool(list_output=list_output)

    result = run_build(fixture, CODE, call_tool, "Blink runner")

    tools = [tool for tool, _ in call_tool.calls]
    assert "tinkercad_create_circuit" in tools
    assert result["reused"] is False
    assert result["circuit_id"] == CIRCUIT_ID
    builds = [c for c in call_tool.calls if c[0] == "tinkercad_build_circuit_model"]
    assert builds[0][1]["clear_existing"] is False


def test_reuse_false_creates_even_with_match():
    fixture = _fixture()
    list_output = json.dumps(
        {"circuits": [{"title": "Blink runner", "id": "existing42"}]}
    )
    call_tool = _fake_call_tool(list_output=list_output)

    result = run_build(fixture, CODE, call_tool, "Blink runner", reuse=False)

    tools = [tool for tool, _ in call_tool.calls]
    assert "tinkercad_list_circuits" not in tools
    assert "tinkercad_create_circuit" in tools
    assert result["reused"] is False
    assert result["circuit_id"] == CIRCUIT_ID
    builds = [c for c in call_tool.calls if c[0] == "tinkercad_build_circuit_model"]
    assert builds[0][1]["clear_existing"] is False


def test_list_failure_falls_back_to_create():
    fixture = _fixture()
    call_tool = _fake_call_tool(fail_list=True)

    result = run_build(fixture, CODE, call_tool, "Blink runner")

    tools = [tool for tool, _ in call_tool.calls]
    assert tools[0] == "tinkercad_list_circuits"
    assert "tinkercad_create_circuit" in tools
    assert result["reused"] is False
    assert result["circuit_id"] == CIRCUIT_ID
    assert result["ok"] is True
    assert result["records"][0].tool == "tinkercad_list_circuits"
    assert result["records"][0].ok is False


def test_list_non_json_falls_back_to_create():
    fixture = _fixture()
    call_tool = _fake_call_tool(list_output="no-json")

    result = run_build(fixture, CODE, call_tool, "Blink runner")

    tools = [tool for tool, _ in call_tool.calls]
    assert "tinkercad_create_circuit" in tools
    assert result["reused"] is False
    assert result["circuit_id"] == CIRCUIT_ID
