"""Documentacion embebida en el propio circuito generado.

El circuito se guarda en Tinkercad y se puede reabrir, pero hasta ahora la
explicacion vivia solo en los reportes del repo: quien abre el diseno ve
cables y un sketch sin contexto. Este modulo arma un bloque de comentario
que viaja *dentro* del proyecto (en el editor de codigo) y se genera desde
la propia fixture, asi que no puede desincronizarse del cableado.

Reglas:
- Todo sale de la fixture: titulo, `doc`, componentes, nets, `oracle`.
- El bloque es un comentario C valido: se puede anteponer a cualquier
  sketch sin cambiar lo que compila.
- Es idempotente: documentar un codigo ya documentado no lo duplica.
"""

from __future__ import annotations

__all__ = ["DOC_MARKER", "render_circuit_doc", "documented_code"]

# Marca que abre el bloque. Sirve para no documentar dos veces.
DOC_MARKER = "/* === DOCUMENTACION DEL CIRCUITO ==="

# Nombres legibles para los tipos de pieza. Es solo para leer mejor: un tipo
# sin entrada usa el slug tal cual, que sigue siendo preciso.
_PRETTY_TYPE = {
    "arduino-uno": "Arduino Uno R3",
    "resistor": "resistencia",
    "capacitor": "capacitor",
    "led": "LED",
    "rgb-led": "LED RGB",
    "pushbutton": "pulsador",
    "potentiometer": "potenciometro",
    "photoresistor": "fotorresistencia (LDR)",
    "buzzer": "piezo / buzzer",
    "timer-555": "temporizador 555",
    "nand-gate": "74HC00 (4 NAND)",
    "xor-gate": "74HC86 (4 XOR)",
    "and-gate": "AND 74HC08",
    "or-gate": "OR 74HC32",
    "not-gate": "NOT 74HC04",
    "shift-register": "74HC595 (registro de desplazamiento)",
    "binary-counter": "74HC93 (contador binario)",
    "decade-counter": "4017 (contador de decadas)",
    "flip-flop-d": "74HC74 (biestable D)",
    "seven-segment": "display 7 segmentos",
    "lcd-16x2": "LCD 16x2",
    "servo": "micro servo",
    "dc-motor": "motor DC",
    "h-bridge-l293d": "puente H L293D",
    "ultrasonic-sensor": "sensor ultrasonico HC-SR04",
    "temperature-sensor": "sensor de temperatura",
    "pir-sensor": "sensor PIR",
    "keypad-4x4": "teclado 4x4",
    "relay-spdt": "rele SPDT",
    "light-bulb": "bombilla",
    "battery-9v": "bateria 9V",
}

_WIDTH = 74


def _pretty(ctype: str) -> str:
    return _PRETTY_TYPE.get(ctype, ctype)


def _wrap(text: str, indent: str = " *   ") -> list[str]:
    """Corta un texto largo en lineas de comentario."""
    words = str(text).split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(indent) + len(candidate) > _WIDTH:
            lines.append(indent + current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(indent + current)
    return lines


def _doc_lines(fixture: dict) -> list[str]:
    doc = fixture.get("doc")
    if isinstance(doc, str):
        return [line.strip() for line in doc.splitlines() if line.strip()]
    if isinstance(doc, list):
        return [str(line).strip() for line in doc if str(line).strip()]
    return []


def _oracle_lines(fixture: dict) -> list[str]:
    oracle = fixture.get("oracle")
    if isinstance(oracle, str):
        return [line.strip() for line in oracle.splitlines() if line.strip()]
    if isinstance(oracle, list):
        return [str(line).strip() for line in oracle if str(line).strip()]
    features = fixture.get("code_features") or []
    if features:
        return ["El sketch usa: " + ", ".join(str(f) for f in features) + "."]
    return []


def render_circuit_doc(fixture: dict) -> list[str]:
    """Lineas del bloque de documentacion (sin comentario, sin marcas)."""
    title = fixture.get("title") or fixture.get("id") or "Circuito"
    lines: list[str] = [f"CONTADOR / CIRCUITO: {title}"]

    ref = fixture.get("id") or ""
    if ref:
        lines.append(f"Fixture del cerebro: {ref}")
    tinkercad_id = fixture.get("tinkercad_id")
    if tinkercad_id:
        lines.append(f"Diseno en Tinkercad: /things/{tinkercad_id}/editel")

    lines.append("")
    lines.append("QUE HACE")
    doc = _doc_lines(fixture)
    if doc:
        for entry in doc:
            lines.extend(_wrap(entry))
    else:
        components = fixture.get("components") or []
        nets = fixture.get("nets") or []
        lines.append(
            f"  {len(components)} piezas y {len(nets)} nets. El titulo de "
            "arriba resume el comportamiento; el cableado de abajo es el "
            "que esta dibujado en el lienzo."
        )

    components = fixture.get("components") or []
    if components:
        lines.append("")
        lines.append("COMPONENTES (ref  tipo  pieza)")
        width = max(len(str(c.get("ref", ""))) for c in components)
        for component in components:
            ref_name = str(component.get("ref", ""))
            ctype = str(component.get("type", ""))
            lines.append(f"  {ref_name.ljust(width)}  {ctype:<18} {_pretty(ctype)}")

    nets = fixture.get("nets") or []
    if nets:
        lines.append("")
        lines.append("CABLEADO (cada linea es un nodo: todo esto va unido)")
        for index, net in enumerate(nets, start=1):
            endpoints = [str(point) for point in net]
            body = "  - ".join(endpoints)
            prefix = f"  {index:>2}. "
            if len(prefix) + len(body) <= _WIDTH:
                lines.append(prefix + body)
            else:
                lines.append(prefix + endpoints[0])
                for extra in endpoints[1:]:
                    lines.extend(_wrap("- " + extra, indent=" " * len(prefix)))

    oracle = _oracle_lines(fixture)
    if oracle:
        lines.append("")
        lines.append("COMO SE VERIFICA (serial del simulador)")
        for entry in oracle:
            lines.extend(_wrap(entry))

    notes = fixture.get("notes")
    if isinstance(notes, str):
        notes = [notes]
    if notes:
        lines.append("")
        lines.append("NOTAS")
        for entry in notes:
            lines.extend(_wrap(str(entry)))

    return lines


def render_circuit_doc_text(fixture: dict) -> str:
    """El mismo bloque, en texto plano (para reportes y consola)."""
    return "\n".join(render_circuit_doc(fixture))


def documented_code(fixture: dict, code: str) -> str:
    """Antepone el bloque de documentacion al sketch.

    No toca el codigo: lo deja tal cual debajo del comentario. Si el codigo
    ya trae el bloque (misma marca al inicio, ignorando espacios), se
    devuelve intacto.
    """
    if code is None:
        return code
    if code.lstrip().startswith(DOC_MARKER):
        return code
    body = render_circuit_doc(fixture)
    block = [DOC_MARKER]
    block.extend(" * " + line if line else " *" for line in body)
    block.append(" * ====================================================================== */")
    return "\n".join(block) + "\n" + code
