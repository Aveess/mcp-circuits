"""Pruebas adversarias independientes (tester, fase 0).

No repiten las de test_probe.py / test_fixtures.py / test_metrics.py:
apuntan a salidas no-string, validaciones ausentes en fixtures, extras
ignorados por la metrica, latencias imposibles y falsos positivos de
clasificacion. Un fallo aqui es un hallazgo reportado, no un error del test.
"""

import json
from pathlib import Path

import pytest

from tinkercad_brain.fase0.fixtures import load_fixtures
from tinkercad_brain.fase0.metrics import (
    classify_compile_result,
    compare_circuits,
    latency_summary,
)
from tinkercad_brain.fase0.probe import ProbeStep, records_to_jsonl, run_steps

ROOT = Path(__file__).resolve().parents[1]
REAL_FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"


# ---------------------------------------------------------------- probe


@pytest.mark.parametrize("weird", [123, None, {"k": "v"}, ["a", "b"]])
def test_probe_non_string_output_is_normalized_to_str_in_record_and_jsonl(weird):
    records = run_steps([ProbeStep(tool="weird")], lambda tool, arguments: weird)

    assert records[0].ok is True
    assert isinstance(records[0].output, str)
    parsed = json.loads(records_to_jsonl(records))
    assert isinstance(parsed["output"], str)


def test_probe_empty_steps_returns_empty_and_never_calls_tool():
    calls = []

    def call_tool(tool, arguments):
        calls.append(tool)
        return "should not happen"

    assert run_steps([], call_tool) == []
    assert calls == []
    assert records_to_jsonl(run_steps([], call_tool)) == ""


def test_probe_failure_between_successes_does_not_contaminate_neighbours():
    def call_tool(tool, arguments):
        if tool == "bad":
            raise ValueError("boom-bad")
        return f"out-{tool}"

    records = run_steps(
        [ProbeStep(tool="first"), ProbeStep(tool="bad"), ProbeStep(tool="last")],
        call_tool,
    )

    assert [(r.tool, r.ok, r.output) for r in records] == [
        ("first", True, "out-first"),
        ("bad", False, "boom-bad"),
        ("last", True, "out-last"),
    ]
    assert all(r.elapsed_s >= 0 for r in records)
    lines = records_to_jsonl(records).splitlines()
    assert [json.loads(line)["ok"] for line in lines] == [True, False, True]


def test_probe_default_arguments_dict_is_not_shared_between_steps():
    a, b = ProbeStep(tool="a"), ProbeStep(tool="b")
    a.arguments["x"] = 1
    assert b.arguments == {}


def test_probe_jsonl_escapes_newlines_and_quotes_into_single_line():
    records = run_steps(
        [ProbeStep(tool="noisy")], lambda tool, arguments: 'a\nb "c" \\ d'
    )
    text = records_to_jsonl(records)
    assert len(text.splitlines()) == 1
    assert json.loads(text)["output"] == 'a\nb "c" \\ d'


# ------------------------------------------------------------- fixtures


def _circuit(cid):
    return {
        "id": cid,
        "title": f"Circuit {cid}",
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "led1", "type": "led"},
            {"ref": "r1", "type": "resistor"},
        ],
        "nets": [["uno.D13", "r1.1"], ["r1.2", "led1.anode"], ["led1.cathode", "uno.GND1"]],
        "code_features": ["pinMode"],
    }


def _valid(n=10):
    return [_circuit(f"c{i}") for i in range(n)]


def _write(tmp_path, payload, raw=False):
    p = tmp_path / "circuits.json"
    p.write_text(payload if raw else json.dumps(payload), encoding="utf-8")
    return p


def test_fixtures_malformed_json_raises_value_error(tmp_path):
    with pytest.raises(ValueError):
        load_fixtures(_write(tmp_path, "{not valid json,,,", raw=True))


def test_fixtures_duplicate_endpoint_inside_same_net_is_rejected(tmp_path):
    circuits = _valid()
    circuits[0]["nets"] = [["uno.D13", "uno.D13"], ["led1.cathode", "uno.GND1"]]
    with pytest.raises(ValueError):
        load_fixtures(_write(tmp_path, circuits))


def test_fixtures_empty_net_inside_nets_is_rejected(tmp_path):
    circuits = _valid()
    circuits[0]["nets"] = [["uno.D13", "r1.1"], []]
    with pytest.raises(ValueError):
        load_fixtures(_write(tmp_path, circuits))


def test_fixtures_duplicate_component_ref_inside_one_circuit_is_rejected(tmp_path):
    circuits = _valid()
    circuits[0]["components"].append({"ref": "led1", "type": "resistor"})
    with pytest.raises(ValueError):
        load_fixtures(_write(tmp_path, circuits))


def test_fixtures_non_object_circuit_entry_raises_value_error(tmp_path):
    circuits = _valid()
    circuits[3] = "not-a-circuit"
    with pytest.raises(ValueError):
        load_fixtures(_write(tmp_path, circuits))


def test_fixtures_top_level_object_instead_of_list_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        load_fixtures(_write(tmp_path, {"circuits": _valid()}))


def test_real_fixtures_every_led_circuit_has_a_resistor_participating_in_a_net():
    circuits = load_fixtures(REAL_FIXTURES)
    offenders = []
    for circuit in circuits:
        types = {c["ref"]: c.get("type", "") for c in circuit["components"]}
        has_led = any(t == "led" or t.startswith("led-") for t in types.values())
        if not has_led:
            continue
        refs_in_nets = {ep.partition(".")[0] for net in circuit["nets"] for ep in net}
        resistor_refs = {ref for ref, t in types.items() if t == "resistor"}
        if not (resistor_refs & refs_in_nets):
            offenders.append(circuit["id"])
    assert offenders == []


# -------------------------------------------------------------- metrics


def test_metrics_extra_components_in_actual_do_not_score_perfect():
    expected = {"components": [{"ref": "led1", "type": "led"}], "nets": []}
    actual = {
        "components": [
            {"ref": "led1", "type": "led"},
            {"ref": "r99", "type": "resistor"},
        ],
        "nets": [],
    }
    result = compare_circuits(expected, actual)
    assert result["score"] < 1.0


def test_metrics_extra_nets_in_actual_do_not_score_perfect():
    expected = {"components": [], "nets": [["uno.D13", "led1.anode"]]}
    actual = {
        "components": [],
        "nets": [["uno.D13", "led1.anode"], ["uno.D12", "led1.cathode"]],
    }
    result = compare_circuits(expected, actual)
    assert result["score"] < 1.0


def test_metrics_duplicate_nets_in_actual_do_not_score_perfect():
    expected = {"components": [], "nets": [["uno.D13", "led1.anode"]]}
    actual = {
        "components": [],
        "nets": [["uno.D13", "led1.anode"], ["led1.anode", "uno.D13"], ["uno.D13", "led1.anode"]],
    }
    result = compare_circuits(expected, actual)
    assert result["score"] < 1.0


def test_metrics_latency_single_sample_is_that_sample():
    result = latency_summary({"only": [0.42]})
    assert result["only"] == {"n": 1, "median": 0.42, "worst": 0.42, "mean": 0.42}


def test_metrics_latency_negative_samples_are_rejected():
    with pytest.raises(ValueError):
        latency_summary({"broken": [-1.0, 2.0]})


def test_metrics_latency_empty_mapping_is_empty():
    assert latency_summary({}) == {}


@pytest.mark.parametrize(
    "status,serial",
    [
        ("Compilation finished: 0 errors", ""),
        ("", "0 errors, 0 warnings"),
        ("Simulation running", "0 errors so far"),
    ],
)
def test_metrics_zero_errors_in_success_context_is_not_compile_error(status, serial):
    assert classify_compile_result(status, serial) != "compile_error"


def test_metrics_none_inputs_classify_as_unknown():
    assert classify_compile_result(None, None) == "unknown"
