"""El oráculo del serial: qué marcas tiene que imprimir un circuito.

El serial es la única prueba de comportamiento que da la simulación. Hasta
la fase 44 el runner lo guardaba y no lo miraba: un circuito cuyo sketch
imprime `TEST:ON` / `TEST:OFF` podía reportar `OK: True` con **0 líneas**
capturadas.

Una fixture declara `oracle_serial` con las marcas que prueban su
comportamiento, **en el orden en que deben aparecer**::

    "oracle_serial": ["TEST:ON", "TEST:OFF"]

La comparación es por subcadena literal y avanzando el cursor, así que la
misma marca se puede pedir dos veces (`ON`, `OFF`, `ON`) y `TEST:LED=OFF`
no satisface `TEST:LED=ON`.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List


def check_serial(serial: str, expected: Iterable[str]) -> Dict[str, Any]:
    """Comprueba que cada marca aparezca, en orden, dentro de `serial`.

    Devuelve ``{"ok", "missing", "found"}``. Sin marcas declaradas no hay
    nada que fallar (``ok: True``): la ausencia de contrato no es un error.
    """
    text = serial or ""
    markers: List[str] = [str(m) for m in (expected or []) if str(m)]
    if not markers:
        return {"ok": True, "missing": [], "found": []}

    offset = 0
    found: List[str] = []
    missing: List[str] = []
    for marker in markers:
        index = text.find(marker, offset)
        if index < 0:
            # No se avanza el cursor: la marca siguiente se busca desde el
            # mismo punto, para no encadenar un fallo en cascada.
            missing.append(marker)
            continue
        found.append(marker)
        offset = index + len(marker)
    return {"ok": not missing, "missing": missing, "found": found}
