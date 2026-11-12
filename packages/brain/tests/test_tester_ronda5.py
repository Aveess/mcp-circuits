"""Tester independiente ronda 5: compare_connectivity / normalize / documenter.

Adversarial, sin repetir las suites existentes. Los tests con prefijo
test_BUG_ documentan un fallo esperado: deben fallar hasta que
produccion se corrija (bug = test que falla + reporte).
"""
from tinkercad_brain.documenter import render_build_report
from tinkercad_brain.fase0.metrics import compare_connectivity
from tinkercad_brain.fase0.normalize import normalize_circuit


def _blink_expected():
    return {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "led1", "type": "led"},
            {"ref": "r1", "type": "resistor"},
        ],
        "nets": [
            ["uno.D13", "r1.1"],
            ["r1.2", "led1.anode"],
            ["led1.cathode", "uno.GND1"],
        ],
    }


# ------------------------------------------------------- compare_connectivity
def test_r5_dos_nets_esperadas_que_comparten_gnd_no_son_corto():
    # led1.cathode-GND1 y led2.cathode-GND1 comparten endpoint en expected:
    # tras fusionar no son grupos distintos, asi que unirlas en actual es
    # la tierra comun legitima, no un corto.
    expected = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "led1", "type": "led"},
            {"ref": "led2", "type": "led"},
        ],
        "nets": [
            ["uno.D13", "led1.anode"],
            ["led1.cathode", "uno.GND1"],
            ["led2.cathode", "uno.GND1"],
        ],
    }
    actual = {
        "components": [
            {"ref": "uno", "type": "arduino-uno"},
            {"ref": "a", "type": "led"},
            {"ref": "b", "type": "led"},
        ],
        "nets": [
            ["uno.D13", "a.anode"],
            ["a.cathode", "b.cathode", "uno.GND1"],
        ],
    }
    result = compare_connectivity(expected, actual)
    assert result["shorts"] == []
    assert result["connectivity_score"] == 1.0
    assert result["score"] == 1.0


def test_r5_extra_del_mismo_tipo_con_sus_nets_no_crea_corto_fantasma():
    # Un LED extra entre D13 y GND conecta por pines DISTINTOS (anode y
    # cathode): es una carga, no un cable. No debe aparecer como corto,
    # pero si como extra y castigar components_score.
    expected = _blink_expected()
    actual = {
        "components": expected["components"] + [{"ref": "led9", "type": "led"}],
        "nets": [list(n) for n in expected["nets"]]
        + [["uno.D13", "led9.anode"], ["led9.cathode", "uno.GND1"]],
    }
    result = compare_connectivity(expected, actual)
    assert result["extra_components"] == ["led9"]
    assert result["missing_components"] == []
    assert result["components_score"] == 0.75
    assert result["connectivity_score"] == 1.0
    assert result["shorts"] == []
    assert result["score"] == 0.875


def test_r5_endpoints_sin_par_y_fantasmas_se_descartan_sin_reventar():
    expected = _blink_expected()
    actual = {
        "components": expected["components"] + [{"ref": "led9", "type": "led"}],
        "nets": [
            ["uno.D13", "r1.1", "led9.anode"],
            ["r1.2", "led1.anode"],
            ["led1.cathode", "uno.GND1", "ghost9.1"],
            ["led9.cathode", "ghost9.2"],
        ],
    }
    result = compare_connectivity(expected, actual)
    assert result["extra_components"] == ["led9"]
    assert result["connectivity_score"] == 1.0
    assert result["shorts"] == []
    assert result["score"] == 0.875


def test_r5_expected_sin_nets_no_divide_ni_castiga_conectividad():
    expected = _blink_expected()
    actual = {"components": list(expected["components"]), "nets": []}
    result = compare_connectivity({"components": expected["components"]}, actual)
    assert result["components_score"] == 1.0
    assert result["connectivity_score"] == 1.0
    assert result["score"] == 1.0
    assert result["shorts"] == []
    assert result["missing_components"] == []


def test_r5_actual_sin_componentes_descarta_todas_sus_nets():
    # Las nets literales coinciden con expected, pero sin componentes no
    # hay mapeo posible: ningun endpoint puede darse por conectado.
    expected = _blink_expected()
    actual = {"components": [], "nets": [list(n) for n in expected["nets"]]}
    result = compare_connectivity(expected, actual)
    assert result["components_score"] == 0.0
    assert result["connectivity_score"] == 0.0
    assert result["score"] == 0.0
    assert result["missing_components"] == ["led1", "r1", "uno"]
    assert result["extra_components"] == []
    assert result["shorts"] == []


def test_r5_peligroso_d13_a_la_net_de_gnd_como_cable_de_mas():
    # El caso peligroso, en dos formas que la suite existente no cubre:
    # (a) net extra separada D13-GND1 y (b) D13 agregado a la net de GND,
    # siempre ADEMAS de la net correcta D13-r1.1.
    expected = _blink_expected()
    variants = [
        [list(n) for n in expected["nets"]] + [["uno.D13", "uno.GND1"]],
        [
            ["uno.D13", "r1.1"],
            ["r1.2", "led1.anode"],
            ["led1.cathode", "uno.GND1", "uno.D13"],
        ],
    ]
    for nets in variants:
        actual = {"components": list(expected["components"]), "nets": nets}
        result = compare_connectivity(expected, actual)
        assert ["uno.D13", "uno.GND1"] in result["shorts"], nets
        assert result["score"] == 0.5, nets


def test_BUG_r5_corto_d13_a_otro_pin_gnd_del_uno_no_detectado():
    """D13 cableado a uno.GND2: en un Uno todos los pines GND son la misma
    tierra interna, asi que es el mismo corto que a GND1. Hoy GND2 no esta
    en ninguna net esperada y el corto pasa invisible (score sin castigo,
    e incluso usar GND2 en vez de GND1 para el catodo baja conectividad)."""
    expected = _blink_expected()
    actual = {
        "components": list(expected["components"]),
        "nets": [list(n) for n in expected["nets"]] + [["uno.D13", "uno.GND2"]],
    }
    result = compare_connectivity(expected, actual)
    assert result["shorts"] != []
    assert result["score"] <= 0.5


def test_BUG_r5_corto_via_mismo_pin_de_componente_sin_par_no_detectado():
    """led9.anode aparece en dos nets de actual (D13 y GND): el mismo pin
    fisico es un punto de union, ambas nets son una sola. Al traducir se
    descarta el endpoint sin par ANTES de fusionar nets solapadas, la
    union se pierde y el corto D13-GND no se detecta."""
    expected = _blink_expected()
    actual = {
        "components": expected["components"] + [{"ref": "led9", "type": "led"}],
        "nets": [list(n) for n in expected["nets"]]
        + [["uno.D13", "led9.anode"], ["led9.anode", "uno.GND1"]],
    }
    result = compare_connectivity(expected, actual)
    assert ["uno.D13", "uno.GND1"] in result["shorts"]
    assert result["score"] < 0.875


# ---------------------------------------------------------------- documenter
def test_r5_fidelity_score_cero_se_muestra_como_cero_no_sin_medir():
    doc = render_build_report(
        "Build cero",
        "https://example/c0",
        {"score": 0, "components_score": 0, "connectivity_score": 0},
        "ok",
        [],
    )
    assert "- Fidelidad: 0.0%" in doc
    assert "- Componentes: 0.0% / Conectividad: 0.0%" in doc
    assert "sin medir" not in doc


def test_r5_titulo_con_pipe_y_numeral_no_rompe_la_tabla():
    records = [{"tool": "compile", "ok": True, "elapsed_s": 1.0, "output": "ok"}]
    doc = render_build_report(
        "Build | blink #2", "https://example/c1", {"score": 1.0}, "ok", records
    )
    lines = doc.splitlines()
    assert lines[0] == "# Build | blink #2"
    assert "## Herramientas" in doc
    row = next(line for line in lines if line.startswith("| compile |"))
    assert row == "| compile | 1 | 1.0 | 1.0 |"
    assert row.count("|") == 5


def test_r5_sim_summary_vacio_no_revienta_ni_traga_secciones():
    doc = render_build_report(
        "Build mudo", "https://example/c2", {"score": 1.0}, "", []
    )
    assert "- Simulación: \n" in doc
    assert "- Fidelidad: 100.0%" in doc
    assert "## Herramientas" in doc
    assert "## Fallos" in doc


def test_r5_elapsed_enormes_pero_iguales_se_formatean_finitos():
    records = [
        {"tool": "timer", "ok": True, "elapsed_s": 3153600000.0, "output": "ok"},
        {"tool": "timer", "ok": True, "elapsed_s": 3153600000.0, "output": "ok"},
    ]
    doc = render_build_report("Build lento", "https://example/c3", {}, "ok", records)
    assert "| timer | 2 | 3153600000.0 | 3153600000.0 |" in doc
    assert "inf" not in doc
    assert "nan" not in doc


def test_BUG_r5_mediana_de_elapsed_enormes_sale_inf():
    """Mediana de [1e308, 1e308] debe ser 1e308 (finita): statistics.median
    promedia los dos valores centrales y desborda a inf, y el reporte
    publica 'inf' como mediana de muestras finitas."""
    records = [
        {"tool": "timer", "ok": True, "elapsed_s": 1e308, "output": "ok"},
        {"tool": "timer", "ok": True, "elapsed_s": 1e308, "output": "ok"},
    ]
    doc = render_build_report("Build enorme", "https://example/c4", {}, "ok", records)
    assert "inf" not in doc.lower()
    assert "nan" not in doc.lower()


# ----------------------------------------------------------------- normalize
def _comp(type_, instance_id):
    return {"type": type_, "instance_id": instance_id, "pins": []}


def test_r5_inspect_solo_protoboard_da_cero_componentes_y_cero_nets():
    inspect_data = {"components": [_comp("Breadboard Small", "bb_1")]}
    schematic_data = {
        "nets": [
            {"pins": [
                {"component": "Breadboard Small", "pin": "a1"},
                {"component": "Breadboard Small", "pin": "a2"},
            ]},
            {"pins": [
                {"component": "bb_1", "pin": "b1"},
                {"component": "bb_1", "pin": "b2"},
            ]},
        ]
    }
    assert normalize_circuit(inspect_data, schematic_data) == {
        "components": [],
        "nets": [],
    }


def test_r5_protoboard_intercalado_no_altera_orden_ni_numeracion():
    inspect_data = {
        "components": [
            _comp("LED", "l_a"),
            _comp("Breadboard Small", "bb_1"),
            _comp("LED", "l_b"),
            _comp("Breadboard Small", "bb_2"),
            _comp("Resistor", "r_a"),
        ]
    }
    schematic_data = {
        "nets": [
            {"pins": [
                {"component": "l_b", "pin": "cathode"},
                {"component": "r_a", "pin": "2"},
            ]},
        ]
    }
    assert normalize_circuit(inspect_data, schematic_data) == {
        "components": [
            {"ref": "led1", "type": "led"},
            {"ref": "led2", "type": "led"},
            {"ref": "r1", "type": "resistor"},
        ],
        "nets": [["led2.cathode", "r1.2"]],
    }
