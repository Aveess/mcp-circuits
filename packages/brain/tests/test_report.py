from tinkercad_brain.fase0.report import build_report


def test_empty_records():
    assert build_report([]) == {
        "total_calls": 0,
        "failures": [],
        "latency": {},
        "tools_used": [],
    }


def test_mixed_successes_and_failures_with_known_latencies():
    records = [
        {"tool": "read_circuit", "ok": True, "elapsed_s": 1.0, "output": "ok"},
        {"tool": "compile", "ok": True, "elapsed_s": 2.0, "output": "done"},
        {"tool": "read_circuit", "ok": False, "elapsed_s": 3.0, "output": "boom"},
        {"tool": "compile", "ok": True, "elapsed_s": 4.0, "output": "done again"},
        {"tool": "read_circuit", "ok": True, "elapsed_s": 5.0, "output": "ok again"},
    ]

    report = build_report(records)

    assert report["total_calls"] == 5
    assert report["failures"] == [{"tool": "read_circuit", "output": "boom"}]
    assert report["tools_used"] == ["compile", "read_circuit"]
    # read_circuit: [1.0, 3.0, 5.0] -> median 3.0, worst 5.0
    # compile: [2.0, 4.0] -> median (2+4)/2 = 3.0, worst 4.0
    assert report["latency"]["read_circuit"]["n"] == 3
    assert report["latency"]["read_circuit"]["median"] == 3.0
    assert report["latency"]["read_circuit"]["worst"] == 5.0
    assert report["latency"]["compile"]["n"] == 2
    assert report["latency"]["compile"]["median"] == 3.0
    assert report["latency"]["compile"]["worst"] == 4.0


def test_failures_keep_original_order():
    records = [
        {"tool": "b_tool", "ok": False, "elapsed_s": 0.1, "output": "first failure"},
        {"tool": "a_tool", "ok": True, "elapsed_s": 0.2, "output": "ok"},
        {"tool": "a_tool", "ok": False, "elapsed_s": 0.3, "output": "second failure"},
    ]

    report = build_report(records)

    assert report["failures"] == [
        {"tool": "b_tool", "output": "first failure"},
        {"tool": "a_tool", "output": "second failure"},
    ]
    assert report["tools_used"] == ["a_tool", "b_tool"]


def test_failure_output_truncated_to_200_chars():
    long_output = "x" * 250
    records = [
        {"tool": "compile", "ok": False, "elapsed_s": 1.5, "output": long_output},
    ]

    report = build_report(records)

    assert report["failures"] == [{"tool": "compile", "output": "x" * 200}]
    assert len(report["failures"][0]["output"]) == 200


def test_incomplete_records_missing_elapsed_and_ok():
    records = [
        {"tool": "read_circuit", "output": "no ok key"},
        {"tool": "read_circuit", "ok": True, "output": "no elapsed key"},
        {"tool": "compile", "ok": False, "output": "bad, no elapsed key"},
    ]

    report = build_report(records)

    assert report["total_calls"] == 3
    # Missing "ok" counts as failure; order preserved.
    assert report["failures"] == [
        {"tool": "read_circuit", "output": "no ok key"},
        {"tool": "compile", "output": "bad, no elapsed key"},
    ]
    # Missing "elapsed_s" counts as 0.0 for every record, failures included.
    assert report["latency"]["read_circuit"] == {
        "n": 2,
        "median": 0.0,
        "worst": 0.0,
        "mean": 0.0,
    }
    assert report["latency"]["compile"] == {
        "n": 1,
        "median": 0.0,
        "worst": 0.0,
        "mean": 0.0,
    }
    assert report["tools_used"] == ["compile", "read_circuit"]
