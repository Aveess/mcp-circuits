from tinkercad_brain.verifier import default_blink_contract, evaluate_contract


def sim_result():
    return {
        "samples": [
            {
                "at_ms": 250,
                "sim_time": "00:00:00",
                "leds": {"led1": {"on": True, "level": 0.9}},
                "servos": {"s1": 90},
            },
            {
                "at_ms": 500,
                "sim_time": "00:00:01",
                "leds": {"led1": {"on": True, "level": 0.9}},
                "servos": {"s1": 90},
            },
            {
                "at_ms": 750,
                "sim_time": "00:00:01",
                "leds": {"led1": {"on": False, "level": 0.0}},
                "servos": {"s1": 82},
            },
            {
                "at_ms": 4000,
                "sim_time": "00:00:04",
                "leds": {"led1": {"on": False, "level": 0.0}},
                "servos": {"s1": 95},
            },
        ],
        "serial": "READY\nDONE\n",
    }


def test_full_contract_passes():
    contract = {
        "assertions": [
            {"type": "led", "ref": "led1", "at_ms": 500, "expect_on": True},
            {"type": "led_level", "ref": "led1", "at_ms": 500, "min_level": 0.5},
            {"type": "servo", "ref": "s1", "at_ms": 4000, "angle": 90, "tolerance": 8},
            {"type": "serial_contains", "text": "READY"},
        ]
    }
    out = evaluate_contract(contract, sim_result())
    assert out["passed"] is True
    assert [r["ok"] for r in out["results"]] == [True, True, True, True]
    assert [r["assertion"] for r in out["results"]] == contract["assertions"]


def test_led_failure():
    contract = {
        "assertions": [
            {"type": "led", "ref": "led1", "at_ms": 500, "expect_on": False},
        ]
    }
    out = evaluate_contract(contract, sim_result())
    assert out["passed"] is False
    assert out["results"][0]["ok"] is False


def test_led_level_failure():
    contract = {
        "assertions": [
            {"type": "led_level", "ref": "led1", "at_ms": 750, "min_level": 0.5},
        ]
    }
    out = evaluate_contract(contract, sim_result())
    assert out["passed"] is False
    assert out["results"][0]["ok"] is False


def test_servo_within_tolerance():
    contract = {
        "assertions": [
            {"type": "servo", "ref": "s1", "at_ms": 4000, "angle": 90, "tolerance": 8},
        ]
    }
    out = evaluate_contract(contract, sim_result())
    assert out["passed"] is True


def test_servo_outside_tolerance():
    contract = {
        "assertions": [
            {"type": "servo", "ref": "s1", "at_ms": 750, "angle": 90, "tolerance": 5},
        ]
    }
    # sample at 750 has 82, |82-90|=8 > 5
    out = evaluate_contract(contract, sim_result())
    assert out["passed"] is False
    assert out["results"][0]["ok"] is False


def test_servo_default_tolerance_is_5():
    # 95 vs 90 = 5 -> dentro con default 5
    contract = {
        "assertions": [
            {"type": "servo", "ref": "s1", "at_ms": 4000, "angle": 90},
        ]
    }
    assert evaluate_contract(contract, sim_result())["passed"] is True
    # 82 vs 90 = 8 -> fuera con default 5
    contract2 = {
        "assertions": [
            {"type": "servo", "ref": "s1", "at_ms": 750, "angle": 90},
        ]
    }
    assert evaluate_contract(contract2, sim_result())["passed"] is False


def test_serial_present_and_absent():
    present = {"assertions": [{"type": "serial_contains", "text": "READY"}]}
    absent = {"assertions": [{"type": "serial_contains", "text": "NOT_THERE"}]}
    assert evaluate_contract(present, sim_result())["passed"] is True
    out = evaluate_contract(absent, sim_result())
    assert out["passed"] is False
    assert out["results"][0]["ok"] is False


def test_missing_sample_does_not_raise():
    contract = {
        "assertions": [
            {"type": "led", "ref": "led1", "at_ms": 9999, "expect_on": True},
            {"type": "servo", "ref": "s1", "at_ms": 9999, "angle": 90},
            {"type": "led_level", "ref": "led1", "at_ms": 9999, "min_level": 0.5},
        ]
    }
    out = evaluate_contract(contract, sim_result())
    assert out["passed"] is False
    assert all(r["ok"] is False for r in out["results"])
    assert all(r["detail"] for r in out["results"])


def test_missing_ref_does_not_raise():
    contract = {
        "assertions": [
            {"type": "led", "ref": "nope", "at_ms": 500, "expect_on": True},
            {"type": "servo", "ref": "nope", "at_ms": 500, "angle": 90},
        ]
    }
    out = evaluate_contract(contract, sim_result())
    assert out["passed"] is False
    assert all(r["ok"] is False for r in out["results"])
    assert all(r["detail"] for r in out["results"])


def test_missing_data_structures_do_not_raise():
    contract = {
        "assertions": [
            {"type": "led", "ref": "led1", "at_ms": 500, "expect_on": True},
            {"type": "serial_contains", "text": "READY"},
        ]
    }
    out = evaluate_contract(contract, {})
    assert out["passed"] is False
    assert all(r["ok"] is False for r in out["results"])


def test_unknown_assertion_type():
    contract = {"assertions": [{"type": "bogus", "ref": "led1", "at_ms": 500}]}
    out = evaluate_contract(contract, sim_result())
    assert out["passed"] is False
    assert out["results"][0]["ok"] is False
    assert out["results"][0]["detail"] == "unknown assertion type"


def test_empty_contract_passed_is_false():
    out = evaluate_contract({"assertions": []}, sim_result())
    assert out["passed"] is False
    assert out["results"] == []
    out2 = evaluate_contract({}, sim_result())
    assert out2["passed"] is False
    assert out2["results"] == []


def test_default_blink_contract():
    contract = default_blink_contract()
    assert contract == {
        "assertions": [
            {"type": "led", "ref": "led1", "at_ms": 250, "expect_on": True},
            {"type": "led", "ref": "led1", "at_ms": 750, "expect_on": False},
        ]
    }
    assert evaluate_contract(contract, sim_result())["passed"] is True


def test_default_blink_contract_custom_ref():
    contract = default_blink_contract("led2")
    assert all(a["ref"] == "led2" for a in contract["assertions"])
