import json

from tinkercad_brain.fase0.probe import ProbeRecord, ProbeStep, records_to_jsonl, run_steps


def test_successful_step_records_ok_output_and_nonnegative_elapsed():
    records = run_steps(
        [ProbeStep(tool="ping", arguments={"x": 1})],
        lambda tool, arguments: f"{tool}:{arguments['x']}",
    )

    assert len(records) == 1
    assert records[0].tool == "ping"
    assert records[0].ok is True
    assert records[0].output == "ping:1"
    assert records[0].elapsed_s >= 0


def test_failed_step_records_error_and_next_step_still_runs():
    calls = []

    def call_tool(tool, arguments):
        calls.append(tool)
        if tool == "boom":
            raise RuntimeError("bridge failed")
        return "ok-after"

    records = run_steps(
        [ProbeStep(tool="boom"), ProbeStep(tool="after")],
        call_tool,
    )

    assert calls == ["boom", "after"]
    assert records[0].ok is False
    assert records[0].output == "bridge failed"
    assert records[0].elapsed_s >= 0
    assert records[1].ok is True
    assert records[1].output == "ok-after"


def test_records_preserve_step_order():
    steps = [ProbeStep(tool="c"), ProbeStep(tool="a"), ProbeStep(tool="b")]

    records = run_steps(steps, lambda tool, arguments: tool.upper())

    assert [r.tool for r in records] == ["c", "a", "b"]
    assert [r.output for r in records] == ["C", "A", "B"]


def test_records_to_jsonl_is_parseable_per_line_and_trailing_newline():
    records = [
        ProbeRecord(tool="ping", ok=True, elapsed_s=0.25, output="pong"),
        ProbeRecord(tool="boom", ok=False, elapsed_s=0.0, output="bridge failed"),
    ]

    text = records_to_jsonl(records)

    assert text.endswith("\n")
    lines = text.splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == {
        "tool": "ping",
        "ok": True,
        "elapsed_s": 0.25,
        "output": "pong",
    }
    assert json.loads(lines[1]) == {
        "tool": "boom",
        "ok": False,
        "elapsed_s": 0.0,
        "output": "bridge failed",
    }


def test_records_to_jsonl_empty_is_empty_string():
    assert records_to_jsonl([]) == ""


def test_probe_step_arguments_default_to_empty_dict():
    assert ProbeStep(tool="ping").arguments == {}
