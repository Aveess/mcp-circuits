from tinkercad_brain.fase0.report import build_report


def _pct(value) -> str:
    return f"{float(value) * 100:.1f}%"


def _seconds(value) -> str:
    return f"{float(value):.1f}"


def render_build_report(
    title: str, circuit_url: str, fidelity: dict, sim_summary: str, records: list[dict]
) -> str:
    report = build_report(records)

    if "score" in fidelity:
        fidelity_line = f"- Fidelidad: {_pct(fidelity['score'])}"
    else:
        fidelity_line = "- Fidelidad: sin medir"

    detail_parts = []
    if "components_score" in fidelity:
        detail_parts.append(f"Componentes: {_pct(fidelity['components_score'])}")
    if "nets_score" in fidelity:
        detail_parts.append(f"Nets: {_pct(fidelity['nets_score'])}")
    elif "connectivity_score" in fidelity:
        detail_parts.append(f"Conectividad: {_pct(fidelity['connectivity_score'])}")

    lines = [
        f"# {title}",
        f"- Circuito: {circuit_url}",
        "",
        "## Verificación",
        fidelity_line,
    ]
    if detail_parts:
        lines.append("- " + " / ".join(detail_parts))
    lines.append(f"- Simulación: {sim_summary}")
    lines.append("")
    lines.append("## Herramientas")
    if not records:
        lines.append("Sin registros.")
    else:
        lines.append("| tool | n | mediana (s) | peor (s) |")
        lines.append("| --- | --- | --- | --- |")
        for tool in sorted(report["latency"]):
            stats = report["latency"][tool]
            lines.append(
                f"| {tool} | {stats['n']} | "
                f"{_seconds(stats['median'])} | {_seconds(stats['worst'])} |"
            )
    lines.append("")
    lines.append("## Fallos")
    if report["failures"]:
        for failure in report["failures"]:
            lines.append(f"- {failure['tool']}: {failure['output']}")
    else:
        lines.append("Sin fallos.")
    return "\n".join(lines) + "\n"
