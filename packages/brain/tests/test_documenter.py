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
