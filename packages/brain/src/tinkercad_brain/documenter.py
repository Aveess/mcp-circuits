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
    build_ok: bool | None = None,
    oracle: dict | None = None,
) -> str:
    report = build_report(records)

    if "score" in fidelity:
        fidelity_line = f"- Fidelidad: {_pct(fidelity['score'])}"
    else:
        fidelity_line = "- Fidelidad: sin medir"
    if fidelity.get("read_failed"):
        # Un 0% que no se midio no acusa al cableado: la inspeccion volvio
        # vacia (la pagina se recargaba) incluso despues de reintentar.
        fidelity_line += (
            f" — **no se pudo leer** el circuito en {fidelity.get('read_attempts', '?')} "
            f"intentos; este porcentaje no mide el cableado"
        )
        if fidelity.get("read_reason") == "editor_not_mounted":
            estado = (fidelity.get("editor_state") or {}).get("text") or "sin datos"
            fidelity_line += (
                f" (el editor no montó el diseño: la página quedó en «{estado}»)"
            )

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
    if build_ok is False:
        # Un build que no se aplico deja el circuito anterior en el editor: la
        # fidelidad y el serial son de ese circuito, y el ruteo no midio nada
        # aunque diga "0 de 4 cables". Decirlo evita leer un reporte mentiroso.
        lines.append(
            "- Build: **no se aplicó** (ver Fallos); lo que sigue mide el "
            "circuito que ya estaba en el editor, no uno nuevo."
        )
    lines.append(f"- Simulación: {sim_summary}")
    lines.append("")
    if oracle is not None:
        lines.append("## Oráculo")
        esperado = oracle.get("expected") or []
        faltan = oracle.get("missing") or []
        if esperado:
            lines.append("- Esperado, en orden: " + " → ".join(f"`{m}`" for m in esperado))
            if faltan:
                lines.append(
                    "- **Falta**: " + ", ".join(f"`{m}`" for m in faltan)
                    + " — el serial no probó el comportamiento."
                )
            else:
                lines.append("- Observado: todas las marcas aparecieron en orden.")
        elif oracle.get("serial_required"):
            if oracle.get("serial_lines", 0) > 0:
                lines.append(
                    f"- Sin marcas declaradas; el sketch imprime "
                    f"({oracle['serial_lines']} líneas)."
                )
            else:
                lines.append(
                    "- **Sin marcas declaradas y sin serial**: el sketch imprime "
                    "y no se capturó nada, así que no hay prueba de comportamiento."
                )
        else:
            lines.append("- Sin marcas declaradas y el sketch no usa `Serial`.")
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
    fallos = [
        f"- {failure['tool']}: {failure['output']}" for failure in report["failures"]
    ]
    # El oráculo no es una tool que falle: si falta una marca o el serial
    # vino vacío, el motivo del OK: False tiene que estar aquí, no solo en la
    # sección de arriba.
    if fidelity.get("read_reason") == "editor_not_mounted":
        estado = (fidelity.get("editor_state") or {}).get("text") or "sin datos"
        fallos.append(
            f"- inspect: el editor no montó el diseño (página en «{estado}»); "
            "no es el cableado"
        )
    if oracle:
        faltan = oracle.get("missing") or []
        if faltan:
            fallos.append("- oráculo: falta " + ", ".join(f"`{m}`" for m in faltan))
        if oracle.get("serial_required") and not oracle.get("serial_lines"):
            fallos.append("- serial: el sketch imprime y no se capturó ninguna línea")
    if fallos:
        for fallo in fallos:
            lines.append(fallo)
    else:
        lines.append("Sin fallos.")
    return "\n".join(lines) + "\n"
