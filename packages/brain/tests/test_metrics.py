from tinkercad_brain.fase0.metrics import (
    classify_compile_result,
    compare_circuits,
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
