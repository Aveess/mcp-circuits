from tinkercad_brain.fase0.report import build_report


def _pct(value) -> str:
    return f"{float(value) * 100:.1f}%"


def _seconds(value) -> str:
    return f"{float(value):.1f}"


def render_build_report(
    title: str,
    circuit_url: str,
    fidelity: dict,
    sim_summary: str,
    records: list[dict],
    route_violations: list[dict] | None = None,
    routes: dict | None = None,
    diagonal_violations: list[dict] | None = None,
    board_hop_diagonals: list[dict] | None = None,
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
    if route_violations is not None:
        measured = (routes or {}).get("measured", 0)
        routed = (routes or {}).get("routed", 0)
        total = (routes or {}).get("total", measured)
        lines.append("## Ruteo")
        if route_violations:
            for violation in route_violations:
                lines.append(
                    f"- {violation['wire']}: tramo horizontal en y="
                    f"{violation['y']:.0f} sobre la placa en x="
                    f"{violation['board']['x']:.0f}"
                )
        else:
            lines.append(
                f"- Sin tramos sobre el cuerpo de una placa "
                f"({measured} de {total} cables medidos, {routed} ruteados)."
            )
        if diagonal_violations:
            for violation in diagonal_violations:
                lines.append(
                    f"- {violation['wire']}: tramo diagonal de "
                    f"{violation['dx']:.0f}x{violation['dy']:.0f} "
                    f"(se rutea en Z, no en recta)"
                )
        elif diagonal_violations is not None:
            lines.append(f"- Sin tramos diagonales en {measured} cables medidos.")
        if board_hop_diagonals:
            worst = max(max(d["dx"], d["dy"]) for d in board_hop_diagonals)
            lines.append(
                f"- {len(board_hop_diagonals)} salto(s) recto(s) entre huecos "
                f"de la placa (max. {worst:.0f} unidades); son puentes, se dejan."
            )
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
