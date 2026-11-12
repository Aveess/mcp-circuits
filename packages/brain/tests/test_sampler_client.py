import json

from tinkercad_brain.sampler_client import simulate_and_verify, to_verifier_format


def sampler_output():
    return {
        "samples": [
            {"at_ms": 250, "led": {"on": True, "level": 0.9}, "sim_time": "00:00:00"},
            {"at_ms": 750, "led": {"on": False, "level": 0.0}, "sim_time": None},
        ],
        "serial": None,
        "errors": [],
    }


class FakeTool:
    def __init__(self, output=None, exc=None):
        self.output = output
        self.exc = exc
        self.calls = []

    def __call__(self, tool, arguments):
        self.calls.append((tool, arguments))
        if self.exc is not None:
            raise self.exc
        return self.output


def test_to_verifier_format_converts_samples_and_none_serial():
    out = to_verifier_format(sampler_output())
    assert out == {
        "samples": [
            {
                "at_ms": 250,
                "sim_time": "00:00:00",
                "leds": {"led1": {"on": True, "level": 0.9}},
                "servos": {},
            },
            {
                "at_ms": 750,
                "sim_time": None,
                "leds": {"led1": {"on": False, "level": 0.0}},
                "servos": {},
            },
        ],
        "serial": "",
    }


def test_to_verifier_format_custom_ref_serial_passthrough_and_errors_still_convert():
    payload = sampler_output()
    payload["serial"] = "READY\n"
    payload["errors"] = ["something odd"]
    out = to_verifier_format(payload, led_ref="led2")
    assert out["serial"] == "READY\n"
    assert out["samples"][0]["leds"] == {"led2": {"on": True, "level": 0.9}}
    assert len(out["samples"]) == 2


def test_simulate_and_verify_extracts_sorted_unique_times_from_mixed_contract():
    payload = {
        "samples": [
            {"at_ms": 100, "led": {"on": True, "level": 1.0}, "sim_time": None},
            {"at_ms": 250, "led": {"on": True, "level": 0.8}, "sim_time": None},
            {"at_ms": 750, "led": {"on": False, "level": 0.0}, "sim_time": None},
        ],
        "serial": "READY\n",
        "errors": [],
    }
    fake = FakeTool(output=json.dumps(payload))
    contract = {
        "assertions": [
            {"type": "led", "ref": "led1", "at_ms": 750, "expect_on": False},
            {"type": "serial_contains", "text": "READY"},
            {"type": "led_level", "ref": "led1", "at_ms": 250, "min_level": 0.5},
            {"type": "servo", "ref": "s1", "at_ms": 750, "angle": 90},
            {"type": "led", "ref": "led1", "at_ms": 100, "expect_on": True},
        ]
    }
    result = simulate_and_verify(fake, contract)
    assert fake.calls == [
        (
            "tinkercad_simulate_samples",
            {"samples_ms": [100, 250, 750], "led_component": "LED", "read_serial": True},
        )
    ]
    # El servo no existe en la salida del sampler: esa assertion falla,
    # pero los tiempos igual debieron pedirse.
    assert result["raw"] == payload
    assert result["passed"] is False


def test_simulate_and_verify_serial_only_contract_uses_default_250():
    payload = {"samples": [], "serial": "READY\n", "errors": []}
    fake = FakeTool(output=json.dumps(payload))
    contract = {"assertions": [{"type": "serial_contains", "text": "READY"}]}
    result = simulate_and_verify(fake, contract, led_component="LED1")
    assert fake.calls == [
        (
            "tinkercad_simulate_samples",
            {"samples_ms": [250], "led_component": "LED1", "read_serial": True},
        )
    ]
    assert result["passed"] is True
    assert result["raw"] == payload


def test_simulate_and_verify_bridge_error_returns_passed_false_with_error():
    fake = FakeTool(exc=RuntimeError("bridge down"))
    contract = {
        "assertions": [{"type": "led", "ref": "led1", "at_ms": 250, "expect_on": True}]
    }
    result = simulate_and_verify(fake, contract)
    assert result["passed"] is False
    assert result["results"] == []
    assert "bridge down" in result["error"]


def test_simulate_and_verify_invalid_json_returns_passed_false():
    fake = FakeTool(output="not json {{{")
    contract = {
        "assertions": [{"type": "led", "ref": "led1", "at_ms": 250, "expect_on": True}]
    }
    result = simulate_and_verify(fake, contract)
    assert result["passed"] is False
    assert result["results"] == []
    assert result["error"]


def test_simulate_and_verify_blink_end_to_end_passes():
    payload = sampler_output()
    payload["serial"] = "BLINK\n"
    fake = FakeTool(output=json.dumps(payload))
    contract = {
        "assertions": [
            {"type": "led", "ref": "led1", "at_ms": 250, "expect_on": True},
            {"type": "led", "ref": "led1", "at_ms": 750, "expect_on": False},
        ]
    }
    result = simulate_and_verify(fake, contract)
    assert result["passed"] is True
    assert [r["ok"] for r in result["results"]] == [True, True]
    assert result["raw"] == payload
    assert fake.calls[0][1]["samples_ms"] == [250, 750]
