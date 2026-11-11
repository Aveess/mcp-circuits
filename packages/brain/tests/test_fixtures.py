import json
from pathlib import Path

import pytest

from tinkercad_brain.fase0.fixtures import load_fixtures

ROOT = Path(__file__).resolve().parents[1]
REAL_FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"


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
        "code_features": ["pinMode", "digitalWrite"],
    }


def _write(tmp_path, circuits):
    p = tmp_path / "circuits.json"
    p.write_text(json.dumps(circuits), encoding="utf-8")
    return p


def _valid(n=10):
    return [_circuit(f"c{i}") for i in range(n)]


def test_real_fixtures_load_and_have_at_least_10_unique_ids():
    circuits = load_fixtures(REAL_FIXTURES)
    assert len(circuits) >= 10
    ids = [c["id"] for c in circuits]
    assert len(ids) == len(set(ids))


def test_rejects_fewer_than_10_circuits(tmp_path):
    with pytest.raises(ValueError, match="10"):
        load_fixtures(_write(tmp_path, _valid(9)))


def test_rejects_duplicate_ids(tmp_path):
    circuits = _valid(10)
    circuits[1]["id"] = circuits[0]["id"]
    with pytest.raises(ValueError, match="duplicado|duplicate"):
        load_fixtures(_write(tmp_path, circuits))


def test_rejects_circuit_without_components(tmp_path):
    circuits = _valid(10)
    circuits[0]["components"] = []
    with pytest.raises(ValueError, match="components"):
        load_fixtures(_write(tmp_path, circuits))


def test_rejects_circuit_without_nets(tmp_path):
    circuits = _valid(10)
    circuits[0]["nets"] = []
    with pytest.raises(ValueError, match="nets"):
        load_fixtures(_write(tmp_path, circuits))


def test_rejects_net_endpoint_without_ref_pin_format(tmp_path):
    circuits = _valid(10)
    circuits[0]["nets"] = [["unoD13", "led1.anode"]]
    with pytest.raises(ValueError, match="ref\\.pin"):
        load_fixtures(_write(tmp_path, circuits))


def test_rejects_net_endpoint_with_undeclared_ref(tmp_path):
    circuits = _valid(10)
    circuits[0]["nets"] = [["fantasma.D13", "led1.anode"]]
    with pytest.raises(ValueError, match="no declarado|undeclared|fantasma"):
        load_fixtures(_write(tmp_path, circuits))
