"""Fase 38a: el circuito guardado lleva su propia documentacion.

El diseno se puede reabrir en Tinkercad, pero la explicacion vivia solo en
los reportes del repo.  El contrato es: todo build entrega el sketch con un
bloque de comentario generado desde la fixture (titulo, piezas, nets y
oraculo), asi que al abrir el editor de codigo del diseno se lee que hace.
"""

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from tinkercad_brain.circuit_doc import (  # noqa: E402
    DOC_MARKER,
    documented_code,
    render_circuit_doc,
    render_circuit_doc_text,
)

FIXTURES = REPO / "fixtures" / "fase0" / "circuits.json"


def _fixture(fixture_id="contador-555-compuertas"):
    return next(
        f
        for f in json.loads(FIXTURES.read_text(encoding="utf-8"))
        if f.get("id") == fixture_id
    )


def test_la_documentacion_nombra_titulo_piezas_y_cableado():
    fixture = _fixture()
    text = render_circuit_doc_text(fixture)

    assert fixture["title"] in text
    assert fixture["id"] in text
    for component in fixture["components"]:
        assert component["ref"] in text, component
    for net in fixture["nets"]:
        for endpoint in net:
            assert endpoint in text, endpoint


def test_la_documentacion_trae_el_oraculo_de_la_fixture():
    fixture = _fixture()
    text = render_circuit_doc_text(fixture)

    assert "COMO SE VERIFICA" in text
    for line in fixture["oracle"]:
        assert line.split(":")[0] in text


def test_documentacion_de_una_fixture_sin_campos_opcionales():
    minimal = {
        "id": "solo-nets",
        "title": "Circuito minimo",
        "components": [{"ref": "uno", "type": "arduino-uno"}],
        "nets": [["uno.5V", "uno.GND1"]],
    }
    lines = render_circuit_doc(minimal)

    assert any("Circuito minimo" in line for line in lines)
    assert any("QUE HACE" in line for line in lines)
    # Sin `oracle` ni `code_features` no se inventa una seccion vacia.
    assert not any("COMO SE VERIFICA" in line for line in lines)
    assert not any("NOTAS" in line for line in lines)


def test_el_bloque_es_un_comentario_c_valido_y_no_toca_el_sketch():
    fixture = _fixture()
    code = "void setup() {}\n\nvoid loop() {}\n"

    documented = documented_code(fixture, code)

    assert documented.startswith(DOC_MARKER)
    assert documented.endswith(code)
    header = documented[: -len(code)]
    assert header.rstrip().endswith("*/")
    for line in header.splitlines():
        stripped = line.strip()
        assert stripped.startswith("*") or stripped.startswith("/*"), line
    assert header.count("/*") == 1 and header.count("*/") == 1


def test_documentar_dos_veces_no_duplica_el_bloque():
    fixture = _fixture()
    code = "void setup() {}\n"

    once = documented_code(fixture, code)
    twice = documented_code(fixture, once)

    assert twice == once
    assert twice.count(DOC_MARKER) == 1


def test_sin_codigo_no_hay_nada_que_documentar():
    assert documented_code(_fixture(), None) is None


def test_las_27_fixtures_viejas_tambien_se_documentan():
    fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))
    for fixture in fixtures:
        text = render_circuit_doc_text(fixture)
        assert fixture["title"][:20] in text, fixture["id"]
        assert len(text) > 80, fixture["id"]


def test_demo_build_manda_el_sketch_ya_documentado(monkeypatch, tmp_path):
    import demo_build as demo

    captured = {}

    def fake_run_via_bridge(fixture, code, title, **kwargs):
        captured["code"] = code
        captured["fixture"] = fixture
        return {
            "url": "https://www.tinkercad.com/things/XXXXXXXXXXX/editel",
            "fidelity": {"score": 1.0},
            "records": [],
            "serial": "TEST:DIGITO=0",
            "ok": True,
        }

    written = {}

    def fake_write_report(result, fixture, title, reports_dir=None):
        # Respeta la firma real y documenta en el repo que recibio.
        written["doc"] = demo.render_circuit_doc_text(fixture)
        path = tmp_path / f"{fixture['id']}.md"
        path.write_text(written["doc"], encoding="utf-8")
        return path

    monkeypatch.setattr(demo, "run_via_bridge", fake_run_via_bridge)
    # write_report tiene REPORTS_DIR como valor por defecto (se fija al
    # importar), asi que sin este parche el test pisa el reporte real del
    # circuito con la URL falsa.
    monkeypatch.setattr(demo, "write_report", fake_write_report)

    assert demo.main(["contador-555-compuertas"]) == 0
    assert captured["code"].startswith(DOC_MARKER)
    assert "void setup()" in captured["code"]

    # El bloque documenta el cableado del circuito que se acaba de construir.
    assert "CABLEADO" in written["doc"]
    for net in captured["fixture"]["nets"][:5]:
        for endpoint in net:
            assert endpoint in written["doc"], endpoint
    assert (tmp_path / "contador-555-compuertas.md").exists()


def test_select_code_sigue_siendo_el_sketch_puro():
    """El header se agrega al enviar, no en select_code: los tests que
    fijan el texto exacto del sketch siguen valiendo."""
    import demo_build as demo

    fixture = _fixture()
    code = demo.select_code(fixture)

    assert code and not code.startswith(DOC_MARKER)


@pytest.mark.parametrize("fixture_id", ["temporizador-555", "siete-segmentos"])
def test_el_bloque_cabe_en_un_comentario_aunque_el_sketch_sea_largo(fixture_id):
    fixture = _fixture(fixture_id)
    assert len(render_circuit_doc(fixture)) > 5
