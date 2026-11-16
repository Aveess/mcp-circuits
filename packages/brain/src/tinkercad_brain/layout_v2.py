"""Layout v2: integrados insertados en breadboards y puentes cortos.

La v1 dejaba los integrados **libres** fuera de la placa y tendia una estrella
desde el Uno: 140 cables largos, casi todos ruteados por el puente. La v2 los
**inserta** y aprovecha lo que la placa ya hace: los cinco huecos de una media
columna son **un solo nodo** (medido, ver `boards.py`), asi que un cable no
tiene que ir de pata en pata: puede entrar por cualquier hueco libre de la
misma media columna. De ahi salen los puentes cortos y en fila.

Reparto por rol (medido: es el unico que cabe en dos placas grandes):

- **placa 0** los siete integrados de compuertas (7 columnas cada uno).
- **placa 1** los dos JK, el 555, el display y las nueve resistencias.
- **placa 2** una Breadboard Small al costado con los dos capacitores, que en
  la v1 colgaban sueltos a la derecha de todo. Sus patas caen en huecos
  vecinos de la misma fila (medido: `(0, +1)`), asi que el capacitor se
  inserta como cualquier otra pieza y sus cables salen cortos.

Dos reglas que no son esteticas y que el plan hace cumplir:

1. **Ninguna media columna puede recibir dos nets.** Eso es un corto que no se
   ve en la foto: lo detecta `column_conflicts`.
2. **Un integrado con las dos hileras en la misma mitad queda cortado.** Cada
   huella trae sus filas en mitades distintas y el layout ancla en la fila de
   `_ANCHOR`, que es la que dejo una hilera por mitad al medirla en vivo.

Los cables se tienden **en fila**: cada net elige un renglon por mitad y los
puentes van de hueco a hueco de ese mismo renglon (``12d -> 19d``), asi que no
hay diagonales. Cuando un net tiene patas en las dos mitades de la placa, el
cruce va por una **columna libre** (un hueco arriba y otro abajo, unidos por un
cable vertical): eso es un puente que cruza el canal, como en un montaje real.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from tinkercad_brain.boards import (
    ROW_Y,
    board,
    footprint_for,
    half,
    hole,
    model_pin,
    x_of,
)
from tinkercad_brain.layout import LayoutError

__all__ = ["column_conflicts", "footprint_for", "plan_layout_v2", "plan_nets_v2"]

_UNO = "arduino-uno"

# Pieza -> fila/pin del ancla. Medido en vivo: el ancla es el pin 1 del DIP y la
# fila es la que deja una hilera por cada mitad de la placa.
_ANCHOR: Dict[str, str] = {
    "and-gate": "1A",
    "or-gate": "1A",
    "not-gate": "1A",
    "xor-gate": "1A",
    "nand-gate": "1A",
    "flip-flop-jk": "1J",
    "timer-555": "CTRL",
    "seven-segment": "a",
    "resistor": "1",
    "capacitor": "1",
    # El interruptor se ancla por el comun y el pulsador por la pata `1` de la
    # fixture (clave `4` del modelo): las dos anclas quedan en la fila `e`
    # (mitad de arriba) y las demas patas caen solas en las columnas y filas
    # que reporto el modelo (ver `boards.py`).
    "slideswitch": "common",
    "pushbutton": "1",
}

# Angulo medido por pieza (el resto va a 0). El display solo encaja girado:
# con el ancla en la fila `e`, sus cinco patas de arriba quedan a la derecha.
# Medido en jWUw1co8IZH: a 0 grados el puente responde "no angle fits all pins
# in holes" y la fidelidad cae a 33/41 nets. Girar la pieza gira tambien sus
# segmentos, asi que el generador cablea la senal de cada uno por su pata
# opuesta (ver `contador_jk_v2._PIN_GIRADO`) para que el digito se lea derecho.
_ANGLE: Dict[str, int] = {"seven-segment": 180}

# Placa por rol. Es una decision de diseno, no un resultado del algoritmo: las
# compuertas juntas para que el decodificador se lea como bloque.
_BOARD_BY_TYPE: Dict[str, int] = {
    "and-gate": 0,
    "or-gate": 0,
    "not-gate": 0,
    "xor-gate": 0,
    "nand-gate": 0,
    "flip-flop-jk": 1,
    "timer-555": 1,
    "seven-segment": 1,
    "resistor": 1,
    "capacitor": 2,
    # Los dos mandos viven con los capacitores en la placa chica: son las
    # piezas que el usuario pidio ver montadas y no colgando de un cable.
    "slideswitch": 2,
    "pushbutton": 2,
}

# Partes que no se insertan: van libres y el puente las rutea. En la v2 no
# queda ninguna (los capacitores pasaron a la placa 2 al medir su huella),
# pero el camino sigue vivo para piezas sin geometria de huecos.
_FREE_TYPES: frozenset = frozenset()

_GAP_DEFAULT = 2
_GAP = {"resistor": 1}

_FREE_X = 380
_FREE_Y = -250
_FREE_STEP = 200

# Renglones de puente por mitad. Las patas caen en `e`/`f` (y en `b`/`g`/`i`
# segun la pieza), asi que los puentes usan los renglones vecinos: pasan por
# fuera del cuerpo del chip y no tapan ninguna pata.
_ROWS_TOP = ("d", "c", "b", "a")
_ROWS_BOTTOM = ("g", "h", "i", "j")

# Alimentacion con renglon propio, lo mas cerca del borde posible: se leen
# como buses en lugar de mezclarse con las senales.
_POWER_ROWS = {"5V": ("d", "j"), "GND": ("a", "i")}

_SIGNAL_PALETTE = (
    "blue", "green", "orange", "yellow", "purple", "turquoise", "pink", "brown",
)

_POWER_PINS = frozenset({"5V", "VCC", "VDD", "VIN", "3V3"})
# Los comunes del display van a GND en catodo comun: son parte de esa net.
_GND_PINS = frozenset({"GND", "GND1", "GND2", "GND3", "COM1", "COM2", "GROUND"})


# --------------------------------------------------------------------------
# Placas y piezas
# --------------------------------------------------------------------------

def _boards(fixture: dict) -> List[dict]:
    boards = fixture.get("boards")
    if not isinstance(boards, list) or not boards:
        raise LayoutError("layout v2 necesita una lista 'boards'")
    out: List[dict] = []
    for index, entry in enumerate(boards):
        if not isinstance(entry, dict):
            raise LayoutError(f"board {index}: se esperaba un objeto, llego {entry!r}")
        kind = str(entry.get("kind") or "large")
        try:
            table = board(kind)
        except KeyError:
            raise LayoutError(f"board {index}: placa desconocida {kind!r}") from None
        for key in ("x", "y"):
            if not isinstance(entry.get(key, 0), (int, float)) or isinstance(entry.get(key), bool):
                raise LayoutError(f"board {index}: '{key}' tiene que ser numerico")
        # Columna donde arranca el cursor de esta placa. Con dos o tres piezas
        # en una placa chica, empezar en la 1 las deja pegadas al borde.
        start = entry.get("start", 1)
        if not isinstance(start, int) or isinstance(start, bool) or start < 1:
            raise LayoutError(f"board {index}: 'start' tiene que ser un entero >= 1")
        if start > table.columns:
            raise LayoutError(
                f"board {index}: 'start' {start} se pasa de las {table.columns} columnas"
            )
        out.append({
            "kind": kind,
            "x": float(entry.get("x", 0)),
            "y": float(entry.get("y", 0)),
            "start": start,
            "did": table.did,
        })
    return out


def _find_spot(boards: List[dict], cursor: List[int], preferred: int, width: int):
    """Primera columna libre en la placa preferida y, si no cabe, en otra."""
    order = [preferred] + [i for i in range(len(boards)) if i != preferred]
    for index in order:
        if index >= len(boards):
            continue
        columns = board(boards[index]["kind"]).columns
        if cursor[index] + width - 1 <= columns:
            return index, cursor[index]
    return None


def _hole_col(name: str) -> int:
    """Columna de un hueco ``"6e"`` / ``"b1/32e"``."""
    text = str(name).strip()
    if "/" in text:
        text = text.split("/", 1)[1]
    return int(text[:-1])


def _hole_name(col: int, row: str, board_index: int) -> str:
    """Hueco en el lenguaje del puente (``b1/`` cuando no es la primera placa)."""
    return f"b{board_index}/{col}{row}" if board_index else f"{col}{row}"


def plan_layout_v2(fixture: dict) -> dict:
    """Coloca cada pieza en una placa y devuelve ``placements`` y errores."""
    if not isinstance(fixture, dict):
        raise LayoutError("fixture must be a dict")
    components = fixture.get("components")
    if not isinstance(components, list):
        raise LayoutError("fixture must have a 'components' list")
    seen = set()
    for component in components:
        if not isinstance(component, dict) or "ref" not in component or "type" not in component:
            raise LayoutError("each component must have 'ref' and 'type'")
        if component["ref"] in seen:
            raise LayoutError(f"duplicate component ref: {component['ref']!r}")
        seen.add(component["ref"])

    boards = _boards(fixture)
    cursor = [b["start"] for b in boards]
    placements: Dict[str, dict] = {}
    unplaced: List[str] = []
    errors: List[str] = []
    free_index = 0
    free_x = max(b["x"] for b in boards) + _FREE_X
    # Partes que la fixture saca de la placa a proposito. Puede ser una lista
    # de refs (posicion automatica, como las `_FREE_TYPES`) o un dict
    # `{ref: {x, y}}` cuando el dibujo necesita un sitio concreto.
    free_spec = fixture.get("free_parts") or {}
    if isinstance(free_spec, dict):
        free_at: Dict[str, object] = dict(free_spec)
    else:
        free_at = {str(ref): None for ref in free_spec}

    for component in components:
        ref = component["ref"]
        ctype = component["type"]
        if ctype == _UNO:
            continue  # el puente crea el Uno; no es una parte del plan
        if ctype in _FREE_TYPES or ref in free_at:
            spot = free_at.get(ref)
            if isinstance(spot, dict) and "x" in spot and "y" in spot:
                free = {"x": float(spot["x"]), "y": float(spot["y"])}
            else:
                free = {"x": free_x, "y": _FREE_Y - _FREE_STEP * free_index}
                free_index += 1
            placements[ref] = {"free": free, "angle": 0}
            continue
        if ctype not in _ANCHOR:
            unplaced.append(ref)
            errors.append(f"{ref}: sin huella para type {ctype!r}")
            continue

        huella = footprint_for(ctype)
        dcols = [dcol for dcol, _ in huella.values()]
        width = max(dcols) - min(dcols) + 1
        spot = _find_spot(boards, cursor, _BOARD_BY_TYPE[ctype], width)
        if spot is None:
            unplaced.append(ref)
            errors.append(f"{ref}: no cabe en ninguna placa ({width} columnas)")
            continue
        board_index, first = spot
        anchor = first - min(dcols)
        row = huella[_ANCHOR[ctype]][1]
        placements[ref] = {
            "at": hole(boards[board_index]["kind"], anchor, row),
            # El puente ancla por la CLAVE del modelo, no por el nombre de la
            # fixture (ver `MODEL_PIN` en `boards.py`).
            "pin": model_pin(ctype, _ANCHOR[ctype]),
            "angle": _ANGLE.get(ctype, 0),
            "board": board_index,
        }
        cursor[board_index] = first + width + _GAP.get(ctype, _GAP_DEFAULT)

    return {
        "placements": placements,
        "unplaced": unplaced,
        "errors": errors,
        "boards": boards,
    }


# --------------------------------------------------------------------------
# Nets
# --------------------------------------------------------------------------

def _pin_of(endpoint: str) -> str:
    return str(endpoint).split(".", 1)[1] if "." in str(endpoint) else str(endpoint)


def _net_name(net) -> str:
    """Nombre de la net: ``5V``/``GND`` si es alimentacion, si no su pin del Uno."""
    pins = {_pin_of(ep).upper() for ep in net}
    if pins & _POWER_PINS:
        return "5V"
    if pins & _GND_PINS:
        return "GND"
    for endpoint in net:
        if str(endpoint).lower().startswith("uno."):
            return str(endpoint)
    return str(net[0])


def _colors(names: List[str]) -> Dict[str, str]:
    """Un color por net: rojo 5V, negro GND y la paleta en orden alfabetico."""
    mapping = {"5V": "red", "GND": "black"}
    signals = sorted({name for name in names if name not in mapping})
    for index, name in enumerate(signals):
        mapping[name] = _SIGNAL_PALETTE[index % len(_SIGNAL_PALETTE)]
    return mapping


def _rows(name: str, index: int) -> Tuple[str, str]:
    """Renglon de puente para la mitad de arriba y la de abajo."""
    if name in _POWER_ROWS:
        return _POWER_ROWS[name]
    slot = index % len(_ROWS_TOP)
    return _ROWS_TOP[slot], _ROWS_BOTTOM[slot]


def _pick_cross(board_index: int, near_a: int, near_b: int, claims, name: str,
                boards: List[dict], leg_nodes, net_nodes) -> Optional[int]:
    """Columna libre de las dos mitades para cruzar el canal.

    Se elige la que menos cable agrega entre los dos grupos que hay que unir.
    Una columna sirve si sus dos mitades estan libres o ya son de este mismo
    net (unir dos nodos propios no hace dano). Si tiene la pata de otra pieza
    no sirve aunque esa pata no este cableada: el hueco es suyo.
    """
    best = None
    for col in range(1, board(boards[board_index]["kind"]).columns + 1):
        usable = True
        for side in ("top", "bottom"):
            key = (board_index, col, side)
            if key in net_nodes:
                continue
            if key in leg_nodes:
                usable = False
                break
            if key in claims and name not in claims[key]:
                usable = False
                break
        if not usable:
            continue
        cost = abs(col - near_a) + abs(col - near_b)
        if best is None or cost < best[0]:
            best = (cost, col)
    return best[1] if best else None


def _nodes_by_distance(endpoint: str, nodes, boards: List[dict],
                       placements: dict) -> List[Tuple[int, int, str]]:
    """Nodos de placa ordenados por cercania al terminal libre o al Uno."""
    ref = str(endpoint).split(".", 1)[0]
    placement = placements.get(ref) or {}
    free = placement.get("free")
    if ref.lower() != "uno" and isinstance(free, dict):
        free_x = float(free.get("x", 0))

        def distance(key) -> float:
            board_index, col, _ = key
            return abs(
                boards[board_index]["x"] + x_of(boards[board_index]["kind"], col) - free_x
            )

        return sorted(nodes, key=distance)
    return sorted(nodes, key=lambda key: (key[0], key[1]))


def _nearest_node(endpoint: str, nodes, boards: List[dict], placements: dict):
    """Nodo de placa al que se cuelga un terminal libre o un pin del Uno."""
    return _nodes_by_distance(endpoint, nodes, boards, placements)[0]


def _hang_rows(side: str, preferred: str) -> List[str]:
    """Filas de una mitad, empezando por la del net y sin alejarse de ella."""
    filas = [row for row in ROW_Y if half(row) == side]
    filas.sort(key=lambda row: (row != preferred, abs(ROW_Y[row] - ROW_Y[preferred])))
    return filas


def _hang_wire(endpoint: str, nodes, boards: List[dict], placements: dict,
               rows: Tuple[str, str], taken: set, legs: set) -> str:
    """Hueco donde entra el cable de una pata: uno solo por hueco.

    Dos **patas** colgadas del mismo hueco se dibujan como un cable solo (paso
    con los dos capacitores libres, los dos en ``b1/45i``). Un cable de pata si
    puede entrar donde ya termina un puente de la misma fila: asi se ve un tap
    de riel, que es como se cablea el resto del circuito. Como los cinco huecos
    de una media columna son el mismo nodo, correr el cable una fila no cambia
    nada electrico.
    """
    candidatos = _nodes_by_distance(endpoint, nodes, boards, placements)

    def _hole(board_index, col, side):
        return _hole_name(col, rows[0] if side == "top" else rows[1], board_index)

    # Del nodo mas cercano al mas lejano; dentro de cada uno, su renglon y
    # despues los otros renglones de la misma media columna (mismo nodo).
    for board_index, col, side in candidatos:
        preferred = rows[0] if side == "top" else rows[1]
        for row in _hang_rows(side, preferred):
            name = _hole_name(col, row, board_index)
            if name not in taken and name not in legs:
                return name

    return _hole(*candidatos[0])


def plan_nets_v2(fixture: dict, placements: dict) -> dict:
    """Cablea cada net con puentes de hueco a hueco en la misma fila."""
    components = {
        c["ref"]: c for c in fixture.get("components") or [] if isinstance(c, dict)
    }
    boards = _boards(fixture)

    # Pata -> hueco donde la deja el puente al insertar la pieza.
    leg_holes: Dict[str, Tuple[int, int, str]] = {}
    for ref, placement in placements.items():
        if "at" not in placement:
            continue
        ctype = str((components.get(ref) or {}).get("type"))
        huella = footprint_for(ctype)
        anchor = _hole_col(placement["at"])
        board_index = int(placement.get("board") or 0)
        for pin, (dcol, row) in huella.items():
            leg_holes[f"{ref}.{pin}"] = (board_index, anchor + dcol, row)

    legs = set(leg_holes.values())
    leg_nodes = {(b, col, half(row)) for (b, col, row) in legs}
    nets = [list(net) for net in (fixture.get("nets") or [])]
    names = [_net_name(net) for net in nets]
    colors = _colors(names)

    # Nodo = (placa, columna, mitad). Todas las patas de un nodo son el mismo
    # punto electrico: la placa las une, no hace falta cable entre ellas.
    node_sets: List[Dict[Tuple[int, int, str], None]] = []
    for net in nets:
        nodes: Dict[Tuple[int, int, str], None] = {}
        for endpoint in net:
            if endpoint in leg_holes:
                board_index, col, row = leg_holes[endpoint]
                nodes.setdefault((board_index, col, half(row)), None)
        node_sets.append(nodes)

    claims: Dict[Tuple[int, int, str], set] = {}
    for index, nodes in enumerate(node_sets):
        for key in nodes:
            claims.setdefault(key, set()).add(names[index])

    errors: List[str] = []
    crossovers: Dict[Tuple[int, int], int] = {}
    for index, nodes in enumerate(node_sets):
        for board_index in sorted({key[0] for key in nodes}):
            top = sorted(col for (b, col, side) in nodes if b == board_index and side == "top")
            bottom = sorted(col for (b, col, side) in nodes if b == board_index and side == "bottom")
            if not (top and bottom):
                continue
            cross = _pick_cross(
                board_index, top[-1], bottom[0], claims, names[index], boards,
                leg_nodes, set(nodes),
            )
            if cross is None:
                errors.append(
                    f"{names[index]}: sin columna libre en la placa {board_index} "
                    "para cruzar de mitad"
                )
                continue
            crossovers[(index, board_index)] = cross
            for side in ("top", "bottom"):
                claims.setdefault((board_index, cross, side), set()).add(names[index])

    wires: List[dict] = []
    # Huecos que ya reciben el cable de una pata. Sirve para no colgar dos
    # patas del mismo hueco: con dos capacitores libres los dos Terminal 2
    # caian en `b1/45i`.
    pin_holes: set = set()
    legs_by_name = {_hole_name(col, row, b) for (b, col, row) in legs}

    def emit(frm: str, to: str, name: str, color: str) -> None:
        if frm == to:
            # Un cable de un hueco a si mismo no se ve (largo cero) y el
            # puente lo rechaza: mejor un error con nombre que un dibujo roto.
            errors.append(f"{name}: cable de {frm} a si mismo")
            return
        wires.append({"from": frm, "to": to, "net": name, "color": color})
        if "." in frm and "." not in to:
            pin_holes.add(to)
        if "." in to and "." not in frm:
            pin_holes.add(frm)

    for index, net in enumerate(nets):
        name, color = names[index], colors[names[index]]
        nodes = node_sets[index]
        rows = _rows(name, index)
        touched = sorted({key[0] for key in nodes})
        real = [endpoint for endpoint in net if endpoint not in leg_holes]

        for board_index in touched:
            top = sorted(col for (b, col, side) in nodes if b == board_index and side == "top")
            bottom = sorted(col for (b, col, side) in nodes if b == board_index and side == "bottom")
            for cols, row in ((top, rows[0]), (bottom, rows[1])):
                for first, second in zip(cols, cols[1:]):
                    emit(
                        _hole_name(first, row, board_index),
                        _hole_name(second, row, board_index),
                        name, color,
                    )
            if top and bottom:
                cross = crossovers.get((index, board_index))
                if cross is not None:
                    row_top, row_bottom = rows
                    if cross != top[-1]:
                        emit(_hole_name(top[-1], row_top, board_index),
                             _hole_name(cross, row_top, board_index), name, color)
                    if cross != bottom[0]:
                        emit(_hole_name(cross, row_bottom, board_index),
                             _hole_name(bottom[0], row_bottom, board_index), name, color)
                    emit(_hole_name(cross, row_top, board_index),
                         _hole_name(cross, row_bottom, board_index), name, color)

        # Un net que toca dos placas necesita un puente entre ellas: si no, la
        # segunda placa queda sin esa senal y el dibujo no lo muestra.
        for left, right in zip(touched, touched[1:]):
            halves_left = {side for (b, _, side) in nodes if b == left}
            halves_right = {side for (b, _, side) in nodes if b == right}
            common = sorted(halves_left & halves_right)
            if common:
                side = "top" if "top" in common else "bottom"
                row = rows[0] if side == "top" else rows[1]
                col_left = max(col for (b, col, s) in nodes if b == left and s == side)
                col_right = min(col for (b, col, s) in nodes if b == right and s == side)
                emit(_hole_name(col_left, row, left), _hole_name(col_right, row, right),
                     name, color)
                continue
            # Mitades incompatibles: se cruza en la placa de la derecha y el
            # puente sale de la mitad nueva. El cruce arranca en la mitad que
            # la placa derecha YA tiene: empezarlo en la otra seria colgarse
            # de la media columna de otro net (un corto que no falla el build).
            side_left = sorted(halves_left)[0]
            row_left = rows[0] if side_left == "top" else rows[1]
            side_right = sorted(halves_right)[0]
            row_right = rows[0] if side_right == "top" else rows[1]
            col_left = max(col for (b, col, s) in nodes if b == left and s == side_left)
            col_right = min(col for (b, col, s) in nodes if b == right and s == side_right)
            cross = _pick_cross(
                right, col_right, col_right, claims, name, boards, leg_nodes, set(nodes)
            )
            if cross is None:
                errors.append(
                    f"{name}: sin columna libre en la placa {right} para enlazar con la {left}"
                )
                continue
            for extra_side in ("top", "bottom"):
                claims.setdefault((right, cross, extra_side), set()).add(name)
            # Si la columna de cruce ya es la de la pata, el tramo corto sobra:
            # un cable del hueco a si mismo no es un cable.
            if cross != col_right:
                emit(_hole_name(col_right, row_right, right),
                     _hole_name(cross, row_right, right), name, color)
            emit(_hole_name(cross, row_right, right),
                 _hole_name(cross, row_left, right), name, color)
            emit(_hole_name(col_left, row_left, left),
                 _hole_name(cross, row_left, right), name, color)

        if not nodes:
            for first, second in zip(real, real[1:]):
                emit(first, second, name, color)
            continue
        for endpoint in real:
            emit(
                endpoint,
                _hang_wire(endpoint, nodes, boards, placements, rows,
                           pin_holes, legs_by_name),
                name, color,
            )

    return {
        "wires": wires,
        "leg_holes": leg_holes,
        "claims": claims,
        "names": names,
        "errors": errors,
    }


def column_conflicts(nets: dict) -> List[dict]:
    """Medias columnas que reciben mas de un net (un corto que no se ve)."""
    conflicts = []
    for key, owners in sorted((nets.get("claims") or {}).items()):
        if len(owners) > 1:
            board_index, col, side = key
            conflicts.append({
                "board": board_index,
                "column": col,
                "half": side,
                "nets": sorted(owners),
            })
    return conflicts
