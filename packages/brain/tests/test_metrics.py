from tinkercad_brain.fase0.metrics import (
    classify_compile_result,
    compare_circuits,
    compare_connectivity,
    latency_summary,
)


def test_perfect_identity_score_is_one():
    circuit = {
        "components": [{"ref": "led1", "type": "led"}],
        "nets": [["uno.D13", "r1.1"], ["r1.2", "led1.anode"]],
    }
    result = compare_circuits(circuit, circuit)
    assert result["components_score"] == 1.0
    assert result["nets_score"] == 1.0
    assert result["score"] == 1.0
    assert result["missing_components"] == []
    assert result["missing_nets"] == []


def test_missing_component_and_net_scores_and_lists():
    expected = {
        "components": [
            {"ref": "led1", "type": "led"},
            {"ref": "r1", "type": "resistor"},
        ],
        "nets": [["uno.D13", "r1.1"], ["r1.2", "led1.anode"]],
    }
    actual = {
        "components": [{"ref": "led1", "type": "led"}],
        "nets": [["uno.D13", "r1.1"]],
    }
    result = compare_circuits(expected, actual)
    assert result["components_score"] == 0.5
    assert result["nets_score"] == 0.5
    assert result["score"] == 0.5
    assert result["missing_components"] == ["r1"]
    assert result["missing_nets"] == [["led1.anode", "r1.2"]]


def test_component_with_wrong_type_counts_as_missing():
    expected = {"components": [{"ref": "led1", "type": "led"}], "nets": []}
    actual = {"components": [{"ref": "led1", "type": "resistor"}], "nets": []}
    result = compare_circuits(expected, actual)
    assert result["components_score"] == 0.0
    assert result["missing_components"] == ["led1"]


def test_missing_lists_are_sorted():
    expected = {
        "components": [
            {"ref": "z1", "type": "led"},
            {"ref": "a1", "type": "led"},
        ],
        "nets": [["z1.1", "uno.D13"], ["a1.1", "uno.D12"]],
    }
    actual = {"components": [], "nets": []}
    result = compare_circuits(expected, actual)
    assert result["missing_components"] == ["a1", "z1"]
    assert result["missing_nets"] == [["a1.1", "uno.D12"], ["uno.D13", "z1.1"]]


def test_nets_with_endpoints_in_different_order_are_equal():
    expected = {
        "components": [{"ref": "led1", "type": "led"}],
        "nets": [["uno.D13", "r1.1"], ["r1.2", "led1.anode"]],
    }
    actual = {
        "components": [{"ref": "led1", "type": "led"}],
        "nets": [["led1.anode", "r1.2"], ["r1.1", "uno.D13"]],
    }
    result = compare_circuits(expected, actual)
    assert result["nets_score"] == 1.0
    assert result["missing_nets"] == []


def test_empty_expected_does_not_divide_by_zero():
    result = compare_circuits(
        {"components": [], "nets": []},
        {"components": [], "nets": []},
    )
    assert result["components_score"] == 1.0
    assert result["nets_score"] == 1.0
    assert result["score"] == 1.0
    assert result["missing_components"] == []
    assert result["missing_nets"] == []


def _semaforo_expected():
    return {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "led_rojo", "type": "led"},
            {"ref": "led_amarillo", "type": "led"},
            {"ref": "led_verde", "type": "led"},
            {"ref": "r1", "type": "resistor"},
            {"ref": "r2", "type": "resistor"},
            {"ref": "r3", "type": "resistor"},
        ],
        "nets": [
            ["uno.D11", "r1.1"], ["r1.2", "led_rojo.anode"],
            ["led_rojo.cathode", "uno.GND1"],
            ["uno.D10", "r2.1"], ["r2.2", "led_amarillo.anode"],
            ["led_amarillo.cathode", "uno.GND1"],
            ["uno.D9", "r3.1"], ["r3.2", "led_verde.anode"],
            ["led_verde.cathode", "uno.GND1"],
        ],
    }


def test_connectivity_semaforo_unified_ground_generic_refs_score_one():
    actual = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "led1", "type": "led"},
            {"ref": "led2", "type": "led"},
            {"ref": "led3", "type": "led"},
            {"ref": "r1", "type": "resistor"},
            {"ref": "r2", "type": "resistor"},
            {"ref": "r3", "type": "resistor"},
        ],
        "nets": [
            ["uno.D11", "r1.1"], ["r1.2", "led1.anode"],
            ["uno.D10", "r2.1"], ["r2.2", "led2.anode"],
            ["uno.D9", "r3.1"], ["r3.2", "led3.anode"],
            ["led1.cathode", "led2.cathode", "led3.cathode", "uno.GND1"],
        ],
    }
    result = compare_connectivity(_semaforo_expected(), actual)
    assert result["score"] == 1.0
    assert result["components_score"] == 1.0
    assert result["connectivity_score"] == 1.0
    assert result["shorts"] == []
    assert result["missing_components"] == []
    assert result["extra_components"] == []


def test_connectivity_real_short_d13_to_gnd_detected_and_penalized():
    expected = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "led1", "type": "led"},
            {"ref": "r1", "type": "resistor"},
        ],
        "nets": [["uno.D13", "r1.1"], ["r1.2", "led1.anode"],
                 ["led1.cathode", "uno.GND1"]],
    }
    actual = {
        "components": list(expected["components"]),
        "nets": [["uno.D13", "r1.1", "uno.GND1"], ["r1.2", "led1.anode"],
                 ["led1.cathode", "uno.GND1"]],
    }
    result = compare_connectivity(expected, actual)
    assert ["uno.D13", "uno.GND1"] in result["shorts"]
    assert result["shorts"] == sorted(result["shorts"])
    assert result["score"] == 0.5  # (1+1)/2 castigado x0.5 por el corto


def test_connectivity_missing_net_lowers_connectivity():
    expected = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "led1", "type": "led"},
            {"ref": "r1", "type": "resistor"},
        ],
        "nets": [["uno.D13", "r1.1"], ["r1.2", "led1.anode"],
                 ["led1.cathode", "uno.GND1"]],
    }
    actual = {
        "components": list(expected["components"]),
        "nets": [["uno.D13", "r1.1"], ["led1.cathode", "uno.GND1"]],
    }
    result = compare_connectivity(expected, actual)
    assert result["connectivity_score"] < 1.0
    assert result["connectivity_score"] == 2 / 3
    assert result["shorts"] == []


def test_connectivity_extra_component_reported():
    expected = {
        "components": [{"ref": "led_rojo", "type": "led"}],
        "nets": [["led_rojo.anode", "led_rojo.cathode"]],
    }
    actual = {
        "components": [
            {"ref": "led1", "type": "led"},
            {"ref": "led2", "type": "led"},
        ],
        "nets": [["led1.anode", "led1.cathode"], ["led2.anode", "led2.cathode"]],
    }
    result = compare_connectivity(expected, actual)
    assert result["extra_components"] == ["led2"]
    assert result["missing_components"] == []
    assert result["components_score"] == 0.5


def test_connectivity_empty_circuits_no_division_by_zero():
    result = compare_connectivity(
        {"components": [], "nets": []}, {"components": [], "nets": []}
    )
    assert result["score"] == 1.0
    assert result["components_score"] == 1.0
    assert result["connectivity_score"] == 1.0
    assert result["shorts"] == []


def test_latency_summary_known_values_and_empty_list():
    result = latency_summary({"list": [1.0, 2.0, 3.0, 4.0], "read": []})
    assert result["list"] == {"n": 4, "median": 2.5, "worst": 4.0, "mean": 2.5}
    assert result["read"] == {"n": 0, "median": 0.0, "worst": 0.0, "mean": 0.0}


def test_classify_compile_error_english():
    assert classify_compile_result("Failed to compile", "") == "compile_error"
    assert classify_compile_result("", "error: unknown pin") == "compile_error"


def test_classify_compile_error_spanish():
    assert classify_compile_result("No compila el codigo", "") == "compile_error"
    assert classify_compile_result("", "Error de compilacion") == "compile_error"


def test_classify_running():
    assert classify_compile_result("Simulation running", "") == "running"
    assert classify_compile_result("Simulando circuito", "") == "running"


def test_classify_empty_and_ambiguous_is_unknown():
    assert classify_compile_result("", "") == "unknown"
    assert classify_compile_result("Done", "hello") == "unknown"
