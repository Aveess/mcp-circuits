"""Layout v3: la alimentacion entra por la fuente y se reparte por los rieles.

Regla (la fijo Eddie; no es estetica, es la forma en que se arma una placa de
verdad):

1. la fuente es la pieza **Power Supply** (did 111724, pines ``Vcc``/``GND``),
   no el pin de 5V del Uno;
2. de su positivo sale un cable **rojo** al riel positivo de la placa, y de su
   tierra uno **negro** al riel negativo;
3. desde el borde opuesto salen otros dos (uno de cada color) para que la
   placa quede alimentada de punta a punta;
4. cada pieza toca el riel de su propia mitad con un cable corto en su misma
   columna (si esa columna no tiene hueco de riel, al hueco de riel mas
   cercano, en linea recta), en vez de tirar una tirada hasta la fuente;
5. una placa extra se alimenta **de la placa ya alimentada**, no de la fuente,
   con los mismos dos cables y los mismos colores.

Los colores no son decorativos: rojo solo positivo, negro solo tierra. Una net
de senal nunca sale roja ni negra.

La v2 sigue intacta: esto reusa su reparto de piezas y de senales
(``plan_layout_v2`` / ``plan_nets_v2``) y reescribe **solo** las dos nets de
alimentacion.

Que riel le toca a cada polaridad
---------------------------------
El nombre del riel lo pone el modelo y cambia de placa en placa, asi que no se
elige por nombre sino por **lado** (el signo de ``y``: ``top`` son las filas
a..e) y por **distancia a las filas**. Cada net se queda con el riel interior
del lado donde tiene mas patas: sus cables de reparto son verticales y cortos.
El otro riel de ese lado es el destino del cable del borde opuesto, y las patas
de la otra mitad bajan a el (o a una fila de bus si no hay riel libre).

Limites **medidos** del modelo, que este layout respeta:

- en la **placa grande** las dos filas del par de abajo se llaman las dos ``X``
  y son un solo nodo: ese lado solo puede llevar **una** polaridad. El riel
  llega hasta la columna 60 pero **solo 50 columnas tienen hueco** (faltan 6,
  12, 18, 24, 30, 31, 37, 43, 49, 55, 61 y 62): una pata en una de esas
  columnas no puede bajar en vertical, y el cable va al hueco de riel mas
  cercano;
- **una media columna que ya tiene una pata es de esa pata**: la placa une los
  cinco huecos de la mitad, asi que bajar el 5V al hueco ``a58`` es conectar
  el 5V a la pata que este en ``e58``/``f58``. Un bus que aterrice ahi quema
  el integrado (paso el 2026-11-15 con la salida ``4Y`` del XOR). Por eso el
  plan se valida contra las patas antes de construir;
- en la **placa chica** los cuatro rieles son nodos distintos y el cable del
  borde opuesto es el que une los dos del mismo lado, como en una placa real.

De la regla se cae, a proposito, en un solo caso: si el borde opuesto esta
ocupado por la otra polaridad (la placa grande con el positivo abajo), no hay
cable negro al otro borde. El positivo no se mueve porque es el que tiene todas
sus patas de ese lado; la tierra de esa mitad llega por fila de bus.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from tinkercad_brain import layout_v2
from tinkercad_brain.boards import board, half, rail_holes
from tinkercad_brain.layout import LayoutError

__all__ = ["plan_layout_v3", "plan_nets_v3", "rail_at", "rail_on_side"]

_SOURCE_TYPE = "power-supply"
_SOURCE_PINS = {"5V": "Vcc", "GND": "GND"}
_POWER_NAMES = ("5V", "GND")
_COLOR = {"5V": "red", "GND": "black"}

# La fuente va a la izquierda de la primera placa, a media altura.
_SOURCE_DX = 420
_SOURCE_Y = 0
# Columna del riel donde entra cada cable de alimentacion en una placa.
_ENTRY_COLUMN = 1
# La tierra del Uno se cuelga del mismo riel, una columna al lado de la fuente.
_UNO_GROUND_COLUMN = 2

# Renglon de bus por mitad (arriba a..e, abajo f..j) para las patas que no
# pueden tocar su riel. Son los mismos de la v2 para que se lea igual.
_BUS_ROWS = {"5V": ("d", "j"), "GND": ("a", "i")}

# Rieles que el modelo funde en un solo nodo aunque esten en filas distintas:
# la placa grande rotula "X" las dos filas de abajo. Ese lado no puede llevar
# dos polaridades y el cable que las uniria no crea nada.
_SINGLE_NODE_SIDES = {("large", "bottom")}

# Nombre de hueco en el lenguaje de los cables: ``"58f"`` o ``"b1/58f"``.
_HOLE_NAME = re.compile(r"^(?:b(\d+)/)?(\d+)([a-j])$")


# --------------------------------------------------------------------------
# Rieles
# --------------------------------------------------------------------------

def _rails_on_side(kind: str, side: str) -> List[str]:
    """Rieles de un lado fisico, del mas pegado a las filas al mas afuera."""
    rails = board(kind).rails
    names = [
        name for name, y in rails.items() if (y > 0) == (side == "top")
    ]
    return sorted(names, key=lambda name: abs(rails[name]))


def rail_on_side(kind: str, side: str) -> Optional[str]:
    """Riel interior de un lado: el que toca la pieza con el cable mas corto."""
    names = _rails_on_side(kind, side)
    return names[0] if names else None


def rail_at(kind: str, y: int) -> Optional[str]:
    """Riel de la placa a esa altura (o el mas cercano si no hay exacto)."""
    rails = board(kind).rails
    if not rails:
        return None
    for name, ry in rails.items():
        if ry == y:
            return name
    return min(rails, key=lambda name: abs(rails[name] - y))


def _single_node(kind: str, side: str) -> bool:
    return (kind, side) in _SINGLE_NODE_SIDES


def _rail_holes(kind: str) -> Tuple[int, ...]:
    """Columnas con hueco de riel, de menor a mayor."""
    return rail_holes(kind)


def _rail_hole_set(kind: str) -> frozenset:
    return frozenset(_rail_holes(kind))


def _side_of_y(y: int) -> str:
    return "top" if y > 0 else "bottom"


# --------------------------------------------------------------------------
# Nombres de extremo
# --------------------------------------------------------------------------

def _hole(board_index: int, col: int, row: str) -> str:
    name = f"{col}{row}"
    return f"b{board_index}/{name}" if board_index else name


def _rail(board_index: int, rail: str, col: int) -> str:
    name = f"{rail}{col}"
    return f"b{board_index}/{name}" if board_index else name


def _wire(frm: str, to: str, name: str) -> dict:
    return {"from": frm, "to": to, "net": name, "color": _COLOR[name]}


# --------------------------------------------------------------------------
# Piezas
# --------------------------------------------------------------------------

def plan_layout_v3(fixture: dict) -> dict:
    """Como la v2, mas la fuente colocada a la izquierda de la primera placa."""
    if not isinstance(fixture, dict):
        raise LayoutError("fixture must be a dict")
    components = fixture.get("components")
    if not isinstance(components, list):
        raise LayoutError("fixture must have a 'components' list")
    sources = [
        component
        for component in components
        if isinstance(component, dict) and component.get("type") == _SOURCE_TYPE
    ]
    if len(sources) != 1:
        raise LayoutError("el layout v3 necesita exactamente una pieza 'power-supply'")
    source = sources[0]["ref"]
    rest = [component for component in components if component is not sources[0]]
    layout = layout_v2.plan_layout_v2({**fixture, "components": rest})
    boards = layout["boards"]
    if not boards:
        raise LayoutError("el layout v3 necesita al menos una placa")
    layout["placements"][source] = {
        "free": {"x": boards[0]["x"] - _SOURCE_DX, "y": _SOURCE_Y},
        "angle": 0,
    }
    layout["source"] = source
    return layout


# --------------------------------------------------------------------------
# Nets
# --------------------------------------------------------------------------

def plan_nets_v3(fixture: dict, placements: dict) -> dict:
    """Senales con la v2 y alimentacion con la regla de los rieles."""
    nets = [list(net) for net in (fixture.get("nets") or [])]
    names = [layout_v2._net_name(net) for net in nets]
    signal_fixture = {
        **fixture,
        "nets": [net for net, name in zip(nets, names) if name not in _POWER_NAMES],
    }
    signals = layout_v2.plan_nets_v2(signal_fixture, placements)
    power = _plan_power(fixture, signals["leg_holes"], signals["claims"], placements)
    claims = {key: set(owners) for key, owners in (signals["claims"] or {}).items()}
    for key, owners in (power["claims"] or {}).items():
        claims.setdefault(key, set()).update(owners)
    return {
        "wires": power["wires"] + signals["wires"],
        "leg_holes": signals["leg_holes"],
        "claims": claims,
        "names": names,
        "errors": signals["errors"] + power["errors"],
    }


def _cell_owner(leg_holes: dict, owner_by_endpoint: dict) -> Dict[Tuple[int, int, str], str]:
    """{(placa, columna, mitad): net duena} a partir de las patas colocadas.

    Cada pata ocupa una media columna entera (los cinco huecos de esa mitad
    son el mismo nodo), asi que la clave es la media columna y no el hueco.
    """
    owner: Dict[Tuple[int, int, str], str] = {}
    for endpoint, hole in (leg_holes or {}).items():
        board_index, col, row = hole
        name = owner_by_endpoint.get(endpoint)
        if name is None:
            # Una pata que no esta en ninguna net (un pin sin usar) tambien
            # reserva su media columna: nadie mas puede bajar ahi.
            name = f"pata:{endpoint}"
        owner[(board_index, col, half(row))] = name
    return owner


def _foreign_cell_errors(wires: List[dict],
                         cell_owner: Dict[Tuple[int, int, str], str]) -> List[str]:
    """Cables de alimentacion que aterrizan en la media columna de otra net."""
    errors: List[str] = []
    for wire in wires:
        name = str(wire.get("net"))
        for key in ("from", "to"):
            match = _HOLE_NAME.match(str(wire.get(key) or ""))
            if match is None:
                continue
            board_index = int(match.group(1) or 0)
            col = int(match.group(2))
            row = match.group(3)
            owner = cell_owner.get((board_index, col, half(row)))
            if owner is not None and owner != name:
                errors.append(
                    f"{name}: el cable a {wire[key]} cae en la media columna "
                    f"de {owner} (cortocircuito)"
                )
    return errors


def _plan_power(fixture: dict, leg_holes: dict, signal_claims: dict,
                placements: Optional[dict] = None) -> dict:
    boards = layout_v2._boards(fixture)
    components = {
        component["ref"]: component
        for component in fixture.get("components") or []
        if isinstance(component, dict) and "ref" in component
    }
    # Una parte suelta (interruptor, pulsador, fuente) no tiene pata en un
    # hueco: su cable de alimentacion sale de su terminal y va al riel.
    free_refs = {
        ref for ref, placement in (placements or {}).items()
        if isinstance(placement, dict) and "free" in placement
    }
    sources = sorted(
        ref
        for ref, component in components.items()
        if component.get("type") == _SOURCE_TYPE
    )
    if len(sources) != 1:
        return {
            "wires": [],
            "claims": {},
            "errors": ["el layout v3 necesita exactamente una pieza 'power-supply'"],
        }
    source = sources[0]

    wires: List[dict] = []
    errors: List[str] = []
    claims: Dict[Tuple[int, int, str], set] = {}

    # Que pata de cada net de alimentacion cae en que media columna.
    taps: Dict[str, Dict[int, Dict[str, Dict[int, str]]]] = {
        name: {} for name in _POWER_NAMES
    }
    hung: Dict[str, List[str]] = {name: [] for name in _POWER_NAMES}
    for net in fixture.get("nets") or []:
        name = layout_v2._net_name(net)
        if name not in _POWER_NAMES:
            continue
        for endpoint in net:
            if endpoint == f"{source}.{_SOURCE_PINS[name]}":
                continue
            hole = leg_holes.get(endpoint)
            if hole is None:
                hung[name].append(endpoint)
                continue
            board_index, col, row = hole
            taps[name].setdefault(board_index, {}).setdefault(half(row), {})[col] = row

    # Sin pata propia solo pueden colgarse la tierra del Uno (referencia
    # comun) y los terminales de una parte suelta, que se cablean directo al
    # riel. Cualquier otra cosa es un error de la fixture.
    free_power: Dict[str, List[str]] = {name: [] for name in _POWER_NAMES}
    for name in _POWER_NAMES:
        for endpoint in hung[name]:
            if endpoint == "uno.GND1" and name == "GND":
                continue
            if endpoint.split(".", 1)[0] in free_refs:
                free_power[name].append(endpoint)
                continue
            errors.append(
                f"{name}: {endpoint} no es una pata colocada, ni la fuente, "
                "ni la tierra del Uno"
            )
    if errors:
        return {"wires": [], "claims": {}, "errors": errors}

    home = _home_sides(taps)
    powered = sorted({0} | {index for name in _POWER_NAMES for index in taps[name]})

    # Dueno de cada pata: la net de la fixture a la que pertenece. Sirve para
    # dos cosas: no dejar que un bus baje en una media columna ajena (un chip
    # tiene una pata por media columna, asi que tocar su hueco es tocar su
    # pata) y para el chequeo final de cortos.
    owner_by_endpoint: Dict[str, str] = {}
    for net in fixture.get("nets") or []:
        name = layout_v2._net_name(net)
        for endpoint in net:
            owner_by_endpoint[endpoint] = name
    cell_owner = _cell_owner(leg_holes, owner_by_endpoint)

    # Quien es dueno de cada media columna: senales y patas de alimentacion.
    occupied: Dict[Tuple[int, int, str], set] = {
        key: set(owners) for key, owners in (signal_claims or {}).items()
    }
    # Las patas de TODAS las piezas, no solo las de alimentacion: una media
    # columna que ya tiene una pata no se puede usar como bajada de bus aunque
    # el trazado de senales no la haya reclamado.
    for cell, owner in cell_owner.items():
        occupied.setdefault(cell, set()).add(owner)
    for name in _POWER_NAMES:
        for index, sides in taps[name].items():
            for side, cols in sides.items():
                for col in cols:
                    occupied.setdefault((index, col, side), set()).add(name)

    taken: Dict[int, set] = {}

    # 1) La fuente entra al riel de cada net en la placa 0.
    for name in _POWER_NAMES:
        rail = rail_on_side(boards[0]["kind"], home[name])
        if rail is None:
            errors.append(f"{name}: la placa 0 no tiene riel para la alimentacion")
            continue
        wires.append(
            _wire(
                f"{source}.{_SOURCE_PINS[name]}",
                _rail(0, rail, _ENTRY_COLUMN),
                name,
            )
        )
        taken.setdefault(0, set()).add(_ENTRY_COLUMN)

    # 2) La tierra del Uno se cuelga del mismo riel, al lado de la fuente.
    if "uno.GND1" in hung["GND"]:
        rail = rail_on_side(boards[0]["kind"], home["GND"])
        wires.append(
            _wire("uno.GND1", _rail(0, rail, _UNO_GROUND_COLUMN), "GND")
        )
        taken.setdefault(0, set()).add(_UNO_GROUND_COLUMN)

    # 2b) Terminales de partes sueltas (el interruptor del EN, el pulsador del
    #     RESET): cable directo de su terminal al riel de su net, entrando por
    #     el borde izquierdo como la fuente.
    for name in _POWER_NAMES:
        if not free_power[name]:
            continue
        rail = rail_on_side(boards[0]["kind"], home[name])
        if rail is None:
            errors.append(f"{name}: la placa 0 no tiene riel para la alimentacion")
            continue
        used = taken.setdefault(0, set())
        for endpoint in free_power[name]:
            col = _nearest_rail_column(boards[0]["kind"], _ENTRY_COLUMN, used)
            if col is None:
                errors.append(
                    f"{name}: sin hueco de riel para el cable de {endpoint}"
                )
                continue
            wires.append(_wire(endpoint, _rail(0, rail, col), name))
            used.add(col)

    # 3) Placa extra: dos cables desde la ultima placa ya alimentada, de riel a
    #    riel y a la misma altura, asi que salen rectos.
    previous = 0
    for index in powered:
        if index == 0:
            continue
        for name in _POWER_NAMES:
            near = rail_on_side(boards[previous]["kind"], home[name])
            far = rail_on_side(boards[index]["kind"], home[name])
            if near is None or far is None:
                errors.append(
                    f"{name}: falta riel para unir la placa {previous} con la {index}"
                )
                continue
            wires.append(
                _wire(
                    _rail(previous, near, max(_rail_holes(boards[previous]["kind"]))),
                    _rail(index, far, _ENTRY_COLUMN),
                    name,
                )
            )
        previous = index

    # 4) Reparto en cada placa: riel del lado, o bus si el riel no llega.
    for index in powered:
        kind = boards[index]["kind"]
        other = {
            "5V": home["GND"],
            "GND": home["5V"],
        }
        for name in _POWER_NAMES:
            sides = taps[name].get(index) or {}
            _distribute(name, index, kind, home[name], other[name], sides,
                        occupied, claims, taken, wires, errors)

    # 5) Un cable de alimentacion que aterrice en la media columna de una pata
    #    ajena es un corto: la placa une los cinco huecos de la mitad, asi que
    #    tocar el hueco es tocar la pata. Se falla antes de construir (el
    #    simulador, si no, quema el integrado).
    errors.extend(_foreign_cell_errors(wires, cell_owner))

    return {"wires": wires, "claims": claims, "errors": errors}


def _home_sides(taps: Dict[str, Dict[int, Dict[str, Dict[int, str]]]]) -> Dict[str, str]:
    """Lado de cada net, eligiendo el reparto que menos cables de bus pide.

    Cada net va a un lado distinto: un lado lleva una sola polaridad, y asi el
    cable del borde opuesto siempre tiene a donde llegar (en la placa grande el
    par de abajo es un solo nodo, o sea que ahi la regla no es opcional).

    El criterio es cuantitativo: se prueban los dos repartos y gana el que deja
    menos patas del lado equivocado, que son las que necesitan fila de bus.
    Empate: ``5V`` abajo, que es donde lo deja el netlist de los integrados.
    """
    votes: Dict[str, Dict[str, int]] = {
        name: {"top": 0, "bottom": 0} for name in _POWER_NAMES
    }
    for name in _POWER_NAMES:
        for sides in taps[name].values():
            for side, cols in sides.items():
                votes[name][side] += len(cols)
    across = {"top": "bottom", "bottom": "top"}

    best: Optional[Tuple[Tuple[int, int], Dict[str, str]]] = None
    for side_5v in ("bottom", "top"):
        side_gnd = across[side_5v]
        cost = votes["5V"][across[side_5v]] + votes["GND"][across[side_gnd]]
        rank = (cost, 0 if side_5v == "bottom" else 1)
        if best is None or rank < best[0]:
            best = (rank, {"5V": side_5v, "GND": side_gnd})
    return best[1]


def _distribute(name: str, index: int, kind: str, side: str, other_side: str,
                sides: dict, occupied: dict, claims: dict,
                taken: Dict[int, set], wires: List[dict], errors: List[str]) -> None:
    """Patas de esta net en esta placa: al riel de su lado o por bus."""
    home_rail = rail_on_side(kind, side)
    if home_rail is None:
        if sides:
            errors.append(f"{name}: la placa {kind} no tiene riel")
        return
    rail_set = _rail_hole_set(kind)

    # El borde opuesto: el riel interior del otro lado, si no lo ocupa la otra
    # polaridad. Si lo ocupa, no hay cable (ver el docstring del modulo).
    far_rail: Optional[str] = None
    if other_side != side:
        candidates = [
            rail
            for rail in _rails_on_side(kind, other_side)
            if not _same_rail_node(kind, rail, home_rail)
        ]
        other_home = rail_on_side(kind, other_side)
        candidates = [rail for rail in candidates if rail != other_home]
        if not _single_node(kind, other_side):
            far_rail = candidates[0] if candidates else None
        else:
            # Lado fusionado: lleva una sola polaridad y es la del net que ya
            # lo tiene de casa; el otro color no puede entrar ahi.
            far_rail = None

    for half_side in ("top", "bottom"):
        cols = sides.get(half_side) or {}
        if not cols:
            continue
        same_side = half_side == side
        target = home_rail if same_side else far_rail
        # Un tap vertical solo vale si el riel tiene hueco en esa columna: en
        # la placa grande faltan seis (24, 37, 43...).
        direct = {
            col: row
            for col, row in cols.items()
            if target is not None and col in rail_set
        }
        rest = {col: row for col, row in cols.items() if col not in direct}
        for col, row in sorted(direct.items()):
            wires.append(_wire(_hole(index, col, row), _rail(index, target, col), name))
            taken.setdefault(index, set()).add(col)
        if rest and target is not None and same_side:
            # La pata ya esta del lado de su riel: el cable va del hueco de la
            # pata al hueco de riel mas cercano, sin pasar por ningun hueco de
            # dato ajeno. Un bus aqui seria un corto por construccion: la
            # media columna de la bajada es la pata de otro.
            for col, row in sorted(rest.items()):
                rail_col = _nearest_rail_column(kind, col, taken.setdefault(index, set()))
                if rail_col is None:
                    errors.append(
                        f"{name}: sin hueco de riel cerca de la columna {col} "
                        f"en la placa {index}"
                    )
                    continue
                tap = _wire(_hole(index, col, row), _rail(index, target, rail_col), name)
                # Si la columna de la pata no tiene hueco de riel, el tap cae
                # en la vecina y la recta saldria inclinada: se pide quiebre
                # en L (el puente lo dibuja con un solo punto).
                if rail_col != col:
                    tap["route"] = True
                wires.append(tap)
                taken[index].add(rail_col)
            rest = {}
        if rest:
            _bus(name, index, kind, home_rail, side, half_side, rest,
                 occupied, claims, taken, wires, errors)

    # El cable al borde opuesto, en el ultimo hueco del riel: es el que
    # alimenta el otro extremo de la placa.
    if far_rail is not None:
        col = _edge_column(index, kind, taken)
        if col is None:
            errors.append(
                f"{name}: sin columna para el cable del borde opuesto en la placa {index}"
            )
        else:
            wires.append(_wire(_rail(index, home_rail, col), _rail(index, far_rail, col), name))


def _nearest_rail_column(kind: str, col: int, used: set) -> Optional[int]:
    """Hueco de riel mas cercano a ``col`` que no este ocupado por otro cable."""
    holes = sorted(_rail_holes(kind), key=lambda hole: (abs(hole - col), hole))
    for hole in holes:
        if hole not in used:
            return hole
    return None


def _same_rail_node(kind: str, first: str, second: str) -> bool:
    """Si dos rieles son el mismo nodo del modelo (la grande funde su par bajo)."""
    if first == second:
        return True
    y_first = board(kind).rails[first]
    y_second = board(kind).rails[second]
    same_side = _side_of_y(y_first) == _side_of_y(y_second)
    return same_side and _single_node(kind, _side_of_y(y_first))


def _bus(name: str, index: int, kind: str, home_rail: str, side: str,
         half_side: str, cols: dict, occupied: dict, claims: dict,
         taken: Dict[int, set], wires: List[dict], errors: List[str]) -> None:
    """Bajada desde el riel alimentado a una fila de bus, y la fila de bus."""
    home_y = board(kind).rails[home_rail]
    drop = _drop_column(index, kind, name, home_y, half_side, cols, occupied, taken)
    if drop is None:
        errors.append(
            f"{name}: sin columna libre en la placa {index} para la bajada"
        )
        return
    row = _BUS_ROWS[name][0 if half_side == "top" else 1]
    path = sorted(set(cols) | {drop})
    for left, right in zip(path, path[1:]):
        wires.append(_wire(_hole(index, left, row), _hole(index, right, row), name))
    wires.append(_wire(_rail(index, home_rail, drop), _hole(index, drop, row), name))
    claims.setdefault((index, drop, half_side), set()).add(name)


def _drop_column(index: int, kind: str, name: str, home_y: int, half_side: str,
                 cols: dict, occupied: dict, taken: Dict[int, set]) -> Optional[int]:
    """Columna de la bajada: una del net o una libre, lo mas al borde posible.

    Si la bajada cae del mismo lado del riel no cruza nada: solo importa la
    mitad donde aterriza. Si viene del otro lado el cable cruza la placa
    entera, asi que las dos mitades tienen que ser del net (o estar libres).
    """
    used = taken.setdefault(index, set())
    crossing = _side_of_y(home_y) != half_side
    rail_set = _rail_hole_set(kind)

    def usable(col: int, own: bool, halves: tuple) -> bool:
        if col in used or col not in rail_set:
            return False
        for other in halves:
            owners = occupied.get((index, col, other)) or set()
            if own:
                if owners - {name}:
                    return False
            elif owners:
                return False
        return True

    # Orden de preferencia: columna del propio net (la bajada queda pegada a
    # sus patas), luego una libre. Cuando la bajada viene del otro lado se
    # prefiere ademas una columna con las dos mitades despejadas, pero no se
    # exige: el cable lo rutea el puente por carril, y exigirlo dejaba sin
    # bajada a cualquier placa con las dos mitades ocupadas por integrados.
    passes = [("top", "bottom"), (half_side,)] if crossing else [(half_side,)]
    for own in (True, False):
        for halves in passes:
            for col in sorted(set(cols) & rail_set, reverse=True) if own else sorted(rail_set, reverse=True):
                if usable(col, own, halves):
                    used.add(col)
                    return col
    return None


def _edge_column(index: int, kind: str, taken: Dict[int, set]) -> Optional[int]:
    """Ultimo hueco de riel que no use nadie: ahi va el cable del borde."""
    used = taken.setdefault(index, set())
    for col in sorted(_rail_holes(kind), reverse=True):
        if col not in used:
            used.add(col)
            return col
    return None
