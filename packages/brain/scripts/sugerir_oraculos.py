"""Borrador de contratos de oraculo a partir de los seriales medidos.

Lee `docs/reportes/<fixture>.md`, saca las lineas del serial de la seccion
"Simulación" y propone `oracle_serial` para cada fixture: las marcas TEST:
que de verdad aparecieron en la ventana medida, en su orden de aparicion.

No decide por su cuenta: imprime la propuesta para revisarla y declararla a
mano en `fixtures/fase0/circuits.json`.

Uso: python sugerir_oraculos.py [--json]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTES = ROOT / "docs" / "reportes"
FIXTURES = ROOT / "fixtures" / "fase0" / "circuits.json"


def lineas_del_reporte(path: Path) -> list[str]:
    """Extrae `lines` del bloque JSON de la seccion Simulacion."""
    text = path.read_text(encoding="utf-8")
    start = text.find("- Simulación: ")
    if start < 0:
        return []
    bloque = text[start + len("- Simulación: "):]
    end = bloque.find("\n\n## ")
    if end >= 0:
        bloque = bloque[:end]
    try:
        data = json.loads(bloque)
    except json.JSONDecodeError:
        return []
    return [str(l) for l in (data.get("lines") or [])]


def marcas(lineas: list[str]) -> list[str]:
    """Marcas TEST: en orden de aparicion (sin duplicados consecutivos)."""
    out: list[str] = []
    for linea in lineas:
        for m in re.findall(r"TEST:[A-Z0-9_]+(?:=[A-Z0-9_.-]+)?", linea):
            if m not in out:
                out.append(m)
    return out


def main() -> int:
    fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))
    propuestas = {}
    for fixture in fixtures:
        fid = fixture["id"]
        path = REPORTES / f"{fid}.md"
        if not path.exists():
            print(f"{fid:30} SIN REPORTE")
            continue
        lineas = lineas_del_reporte(path)
        encontradas = marcas(lineas)
        propuestas[fid] = encontradas
        print(f"{fid:30} {len(lineas):2} linea(s)  {encontradas}")
    if "--json" in sys.argv:
        print(json.dumps(propuestas, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
