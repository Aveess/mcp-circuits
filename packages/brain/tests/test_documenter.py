from tinkercad_brain.documenter import render_build_report


def test_complete_document_with_compare_circuits_fidelity():
    fidelity = {
        "components_score": 0.5,
        "nets_score": 1.0,
        "score": 0.75,
        "missing_components": ["r1"],
        "missing_nets": [],
    }
    records = [
        {"tool": "read_circuit", "ok": True, "elapsed_s": 1.0, "output": "ok"},
        {"tool": "compile", "ok": True, "elapsed_s": 2.0, "output": "done"},
        {"tool": "read_circuit", "ok": False, "elapsed_s": 3.0, "output": "boom"},
        {"tool": "compile", "ok": True, "elapsed_s": 4.0, "output": "done again"},
        {"tool": "read_circuit", "ok": True, "elapsed_s": 5.0, "output": "ok again"},
    ]

    doc = render_build_report(
        "Build LED",
        "https://www.tinkercad.com/things/abc",
        fidelity,
        "running, sin errores",
        records,
    )

    assert doc.startswith("# Build LED\n")
    assert "- Circuito: https://www.tinkercad.com/things/abc" in doc
    assert "## Verificación" in doc
    assert "- Fidelidad: 75.0%" in doc
    assert "- Componentes: 50.0% / Nets: 100.0%" in doc
    assert "- Simulación: running, sin errores" in doc
    assert "## Herramientas" in doc
    assert "| tool | n | mediana (s) | peor (s) |" in doc
    # Filas ordenadas por nombre de tool: compile antes que read_circuit.
    assert "| compile | 2 | 3.0 | 4.0 |" in doc
    assert "| read_circuit | 3 | 3.0 | 5.0 |" in doc
    assert doc.index("| compile |") < doc.index("| read_circuit |")
    assert "## Fallos" in doc
    assert "- read_circuit: boom" in doc
    # Determinista: mismo input -> mismo texto.
    assert doc == render_build_report(
        "Build LED",
        "https://www.tinkercad.com/things/abc",
        fidelity,
        "running, sin errores",
        records,
    )


def test_fidelity_with_connectivity_score_uses_conectividad_label():
    fidelity = {"score": 0.8, "components_score": 0.9, "connectivity_score": 0.7}
    records = [
        {"tool": "compile", "ok": True, "elapsed_s": 1.5, "output": "done"},
    ]

    doc = render_build_report("Build conn", "https://example/c1", fidelity, "ok", records)

    assert "- Fidelidad: 80.0%" in doc
    assert "- Componentes: 90.0% / Conectividad: 70.0%" in doc
    assert "Nets:" not in doc
    assert "| compile | 1 | 1.5 | 1.5 |" in doc
    assert "Sin fallos." in doc


def test_without_fidelity_reports_sin_medir_and_no_components_line():
    records = [
        {"tool": "compile", "ok": True, "elapsed_s": 2.0, "output": "done"},
    ]

    doc = render_build_report("Build s/f", "https://example/c2", {}, "unknown", records)

    assert "# Build s/f" in doc
    assert "- Fidelidad: sin medir" in doc
    assert "Componentes:" not in doc
    assert "Nets:" not in doc
    assert "Conectividad:" not in doc
    assert "- Simulación: unknown" in doc


def test_without_records_says_sin_registros_and_sin_fallos():
    doc = render_build_report(
        "Build vacío", "https://example/c3", {"score": 1.0}, "ok", []
    )

    assert "- Fidelidad: 100.0%" in doc
    assert "## Herramientas" in doc
    assert "Sin registros." in doc
    assert "| tool |" not in doc
    assert "## Fallos" in doc
    assert "Sin fallos." in doc


def test_failures_listed_in_record_order():
    records = [
        {"tool": "b_tool", "ok": False, "elapsed_s": 0.5, "output": "first failure"},
        {"tool": "a_tool", "ok": True, "elapsed_s": 0.5, "output": "ok"},
        {"tool": "a_tool", "ok": False, "elapsed_s": 0.5, "output": "second failure"},
    ]

    doc = render_build_report("Build fallos", "https://example/c4", {}, "error", records)

    assert "## Fallos" in doc
    assert "- b_tool: first failure" in doc
    assert "- a_tool: second failure" in doc
    assert doc.index("- b_tool: first failure") < doc.index("- a_tool: second failure")
    assert "Sin fallos." not in doc


def test_sin_ruteo_pedido_no_aparece_la_seccion():
    """Un reporte viejo (sin polilineas) no inventa una seccion de ruteo."""
    doc = render_build_report("Build viejo", "https://example/c5", {}, "ok", [])
    assert "## Ruteo" not in doc


def test_ruteo_limpio_dice_cuantos_cables_se_midieron():
    doc = render_build_report(
        "Build limpio", "https://example/c6", {}, "ok", [],
        route_violations=[],
        routes={"routed": 31, "measured": 46, "total": 46},
        diagonal_violations=[],
        board_hop_diagonals=[],
    )
    assert "## Ruteo" in doc
    # Fase 41: el denominador es el total de cables, no solo los ruteados.
    # Antes decia "31 de 31" y escondia los 15 que el puente no tocaba.
    assert "Sin tramos sobre el cuerpo de una placa (46 de 46 cables medidos, 31 ruteados)." in doc
    assert "- Sin tramos diagonales en 46 cables medidos." in doc


def test_ruteo_con_diagonal_nombra_el_cable():
    doc = render_build_report(
        "Build torcido", "https://example/c8", {}, "ok", [],
        route_violations=[],
        routes={"routed": 31, "measured": 46, "total": 46},
        diagonal_violations=[{"wire": "t1.OUT -> u1.1A", "dx": 160.0, "dy": 30.0,
                              "blocking": True}],
        board_hop_diagonals=[],
    )
    assert "- t1.OUT -> u1.1A: tramo diagonal de 160x30 (se rutea en Z, no en recta)" in doc


def test_los_saltos_rectos_de_la_placa_se_cuentan_y_no_rompen():
    doc = render_build_report(
        "Build con puentes", "https://example/c9", {}, "ok", [],
        route_violations=[],
        routes={"routed": 31, "measured": 46, "total": 46},
        diagonal_violations=[],
        board_hop_diagonals=[{"wire": "5g -> 8c", "dx": 30.0, "dy": 60.0,
                              "blocking": False}],
    )
    assert "1 salto(s) recto(s) entre huecos de la placa (max. 60 unidades)" in doc


def test_un_reporte_sin_datos_de_diagonal_no_agrega_la_linea():
    """Callers viejos (sin el dato) no inventan una linea de diagonales."""
    doc = render_build_report(
        "Build sin dato", "https://example/c10", {}, "ok", [],
        route_violations=[], routes={"routed": 3, "measured": 3, "total": 3},
    )
    assert "diagonal" not in doc.lower()


def test_ruteo_con_cruce_nombra_el_cable_y_la_placa():
    doc = render_build_report(
        "Build con cruce", "https://example/c7", {}, "ok", [],
        route_violations=[{
            "wire": "uno.GND1 -> buzzer1.-",
            "y": 106.0,
            "board": {"x": 870.0, "y": 0.0},
        }],
        routes={"routed": 19, "measured": 19},
    )
    assert "## Ruteo" in doc
    assert "- uno.GND1 -> buzzer1.-: tramo horizontal en y=106 sobre la placa en x=870" in doc


def test_un_build_que_no_se_aplico_lo_dice_arriba():
    """El reporte de buzzer-activo decia '0 de 4 cables medidos' como si midiera.

    Cuando el build falla, el circuito que queda en el editor es el anterior:
    la fidelidad y el serial son de ese, y el ruteo no midio nada. Sin esta
    linea el reporte se lee como un circuito sano con ruteo vacio.
    """
    doc = render_build_report(
        "Build no aplicado", "https://example/c11", {"score": 1.0}, "ok", [],
        route_violations=[], routes={"routed": 0, "measured": 0, "total": 4},
        diagonal_violations=[], board_hop_diagonals=[], build_ok=False,
    )
    assert "**no se aplicó**" in doc
    assert "circuito que ya estaba en el editor" in doc


def test_un_build_ok_no_agrega_la_advertencia():
    doc = render_build_report(
        "Build aplicado", "https://example/c12", {"score": 1.0}, "ok", [],
        route_violations=[], routes={"routed": 4, "measured": 4, "total": 4},
        diagonal_violations=[], board_hop_diagonals=[], build_ok=True,
    )
    assert "no se aplicó" not in doc


def test_sin_el_dato_de_build_no_inventa_la_advertencia():
    doc = render_build_report("Build viejo", "https://example/c13", {"score": 1.0}, "ok", [])
    assert "no se aplicó" not in doc
