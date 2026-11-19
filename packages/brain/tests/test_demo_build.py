import importlib.util
import sys
from pathlib import Path

import tinkercad_brain.sketches as sketches

ROOT = Path(__file__).resolve().parents[1]


def _load_demo():
    spec = importlib.util.spec_from_file_location(
        "demo_build", ROOT / "scripts" / "demo_build.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


demo = _load_demo()


def test_fixture_inexistente_error_claro():
    try:
        demo.find_fixture("no-existe")
    except LookupError as exc:
        assert "no-existe" in str(exc)
        assert "no encontrada" in str(exc)
    else:
        raise AssertionError("find_fixture debio lanzar LookupError")

    assert demo.main(["no-existe"]) == 2


def test_select_code_blink():
    fixture = demo.find_fixture("blink-basico")
    code = demo.select_code(fixture)
    assert code == sketches.blink_sketch()
    assert "pinMode(13, OUTPUT)" in code


def test_select_code_servo():
    fixture = demo.find_fixture("servo-potenciometro")
    code = demo.select_code(fixture)
    assert code == sketches.servo_knob_sketch()
    assert "Servo" in code


def test_select_code_sin_sketch_devuelve_none():
    fixture = {"id": "sin-sketch-demo", "components": [], "nets": []}
    assert demo.select_code(fixture) is None


def test_select_code_tmp36_mockeado(monkeypatch):
    # tmp36_sketch puede no existir aun en esta rama: se mockea.
    monkeypatch.setattr(
        sketches, "tmp36_sketch", lambda: "// tmp36 mock\n", raising=False
    )
    fixture = demo.find_fixture("temperatura-tmp36")
    assert demo.select_code(fixture) == "// tmp36 mock\n"


def test_select_code_led_rgb_mockeado(monkeypatch):
    # rgb_cycle_sketch puede no existir aun en esta rama: se mockea.
    monkeypatch.setattr(
        sketches, "rgb_cycle_sketch", lambda: "// rgb mock\n", raising=False
    )
    fixture = demo.find_fixture("led-rgb")
    assert demo.select_code(fixture) == "// rgb mock\n"


def test_select_presets_sensor_ultrasonico():
    fixture = demo.find_fixture("sensor-ultrasonico")
    assert demo.select_presets(fixture) == [
        {
            "component": "Ultrasonic Distance Sensor (4-pin)",
            "property": "Target Y",
            "value": -105,
        }
    ]


def test_select_presets_temporizador_555_fija_valor_y_prefijo():
    fixture = demo.find_fixture("temporizador-555")
    assert demo.select_presets(fixture) == [
        {"component": "Resistor", "property": "resistance", "value": 10, "unit": "k"},
        {"component": "Capacitor", "property": "capacitance", "value": 10, "unit": "u"},
    ]


def test_select_presets_otras_fixtures_sin_presets():
    assert demo.select_presets(demo.find_fixture("blink-basico")) is None


def test_bridge_launch_spec_usa_el_venv_del_puente_si_existe(tmp_path):
    """Puente clonado suelto: su propio `.venv` manda."""
    python = tmp_path / ".venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text("")
    spec = demo.bridge_launch_spec(str(tmp_path))
    assert spec["command"] == str(python)
    assert spec["args"] == ["-m", "src.main"]
    assert spec["cwd"] == str(tmp_path)


def test_bridge_launch_spec_sin_venv_del_puente_usa_el_interprete_actual(tmp_path):
    """Monorepo: el venv esta en la raiz y es el que corre el script.

    Antes se pedia `packages/bridge/.venv/bin/python`, que en el monorepo no
    existe: el runner arrancaba el puente con un interprete fantasma.
    """
    spec = demo.bridge_launch_spec(str(tmp_path))
    assert spec["command"] == sys.executable
    assert spec["args"] == ["-m", "src.main"]
    assert spec["cwd"] == str(tmp_path)


def test_main_rechaza_fixture_sin_sketch_sin_conectar(monkeypatch, capsys):
    calls = []

    def fake_run_via_bridge(*a, **kw):
        calls.append((a, kw))
        return {"url": "x", "fidelity": {"score": 1.0}, "records": [], "ok": True}

    monkeypatch.setattr(demo, "run_via_bridge", fake_run_via_bridge)
    monkeypatch.setattr(
        demo,
        "find_fixture",
        lambda fixture_id: {"id": "sin-sketch-demo", "components": [], "nets": []},
    )

    assert demo.main(["sin-sketch-demo"]) == 2
    assert calls == []
    captured = capsys.readouterr()
    assert "sin sketch" in captured.err
    assert "sin-sketch-demo" in captured.err
