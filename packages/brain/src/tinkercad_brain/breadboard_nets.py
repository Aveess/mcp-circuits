"""Derivación de nets eléctricas desde wires de ``inspect_circuit``.

``inspect_schematic_connections`` devuelve ``nets: []`` en circuitos con
protoboard. Aquí se reconstruyen las nets con union-find sobre los wires,
aplicando la continuidad interna del protoboard:

- Huecos de la misma columna y misma mitad (filas ``f``-``j`` o ``a``-``e``)
  están conectados; el canal central separa ambas mitades.
- Un pin de riel (una sola letra fuera de ``a``-``j`` seguida de columna,
  p. ej. ``z6``) conecta con todos los pines de riel de la misma letra
  del mismo protoboard.

Los endpoints del protoboard no aparecen en el resultado: solo endpoints
reales ``ref.pin``. Solo salen nets con >= 2 endpoints reales, ordenadas
y sin duplicados (inmune a wires duplicados).
"""

import re

from tinkercad_brain.fase0.component_map import fixture_type

# Mapeo mínimo de refs, alineado con fase0.normalize (Arduino->uno,
# LED->ledN, Resistor->rN). Se reutiliza `fixture_type` para el tipo
# canónico en vez de importar la lógica completa de normalize_circuit,
# que no expone el mapa instance_id->ref.
_REF_PREFIX = {
    "led": "led",
    "resistor": "r",
    # Halado por las fixtures (ldr1) y por normalize; sin esto saldria
    # "photoresistor1".
    "photoresistor": "ldr",
}

_PIN_ALIASES = {
    "Terminal 1": "1",
    "Terminal 2": "2",
    "Cathode": "cathode",
    "Anode": "anode",
    "Vcc": "vcc",
    "Vout": "vout",
    "Gnd": "gnd",
}

# Alias que dependen del tipo: p. ej. en un potenciómetro "Terminal 2"
# es el pin "3" de fixture (term1), no el "2" como en una resistencia.
_PIN_ALIASES_BY_TYPE = {
    "servo": {
        "Power": "vcc",
        "Ground": "gnd",
        "Signal": "signal",
    },
    # Acotado a transistor-npn: Collector/Base/Emitter con mayuscula solo
    # los reporta este tipo en vivo (circuito 73azwj2IJDE).
    "transistor-npn": {
        "Collector": "collector",
        "Base": "base",
        "Emitter": "emitter",
    },
    # Acotado a dc-motor: en vivo reporta "Terminal 1"/"Terminal 2", que
    # globalmente serian "1"/"2"; la fixture usa positive(1)/negative(2).
    # Un "1" de resistencia no entra aqui y sigue siendo "1".
    "dc-motor": {
        "1": "positive",
        "2": "negative",
        "Terminal 1": "positive",
        "Terminal 2": "negative",
    },
    # Acotado a battery-9v: en vivo reporta "Positive"/"Negative" con
    # mayuscula; la fixture usa positive/negative. Ningun otro tipo entra
    # aqui (dc-motor/buzzer, que comparten vocabulario, no se ven tocados).
    "battery-9v": {
        "Positive": "positive",
        "Negative": "negative",
    },
    # Acotado a l293d: en los wires de inspect los pines salen con los
    # nombres del esquematico interno (con espacios y "&"); la fixture usa
    # enable1/enable2/vss/vs/inputN/outputN. Los GND ya salen como
    # gnd/gnd1/gnd2/gnd3 y pasan sin cambios.
    "l293d": {
        "Enable 1 & 2": "enable1",
        "Enable 3 & 4": "enable2",
        "Power 1": "vss",
        "Power 2": "vs",
        "Input 1": "input1",
        "Input 2": "input2",
        "Input 3": "input3",
        "Input 4": "input4",
        "Output 1": "output1",
        "Output 2": "output2",
        "Output 3": "output3",
        "Output 4": "output4",
    },
    "potentiometer": {
        "Terminal 1": "1",
        "Terminal 2": "3",
        "Wiper": "2",
    },
    # Acotado a pushbutton: el pulsador de 4 pines reporta en vivo
    # "Terminal 1a"/"Terminal 1b" (un lado, unidos internamente) y
    # "Terminal 2a"/"Terminal 2b" (el otro). El numero del terminal de
    # Tinkercad NO coincide con la numeracion de la fixture
    # boton-pullup (btn1.1 = lado de senal/D2, btn1.2 = lado de
    # tierra): el mapeo se fijo por el circuito real bWmMIRN5dwi
    # (live11.json), donde la net de uno.D2 trae "Terminal 2b" y la
    # de uno.GND1 trae "Terminal 1a". Los "Terminal 1"/"Terminal 2"
    # sin letra de la resistencia no entran aqui y siguen en 1/2.
    "pushbutton": {
        "Terminal 1a": "2",
        "Terminal 1b": "2",
        "Terminal 2a": "1",
        "Terminal 2b": "1",
    },
    "ultrasonic-hcsr04": {
        "Power": "vcc",
        "Trigger": "trig",
        "Echo": "echo",
        "Ground": "gnd",
    },
    # Acotado a buzzer: en vivo el Piezo reporta los terminales "+"/"-"
    # (circuito cZcqbZ3eNlA); la fixture usa positive/negative.
    # El Piezo expone las patas como "+"/"-" en inspect, pero los wires
    # vivos (circuito 93Dj8w6iEv1) las etiquetan "Positive"/"Negative".
    "buzzer": {
        "+": "positive",
        "-": "negative",
        "Positive": "positive",
        "Negative": "negative",
    },
    # Acotado a photoresistor: el LDR real ("Photoresistor (LDR)") reporta
    # "terminal-1"/"terminal-2"; la fixture usa 1/2.
    "photoresistor": {
        "terminal-1": "1",
        "terminal-2": "2",
        "Terminal 1": "1",
        "Terminal 2": "2",
    },
    # Acotado a este tipo: "Red"/"Green"/"Blue" con mayuscula solo los
    # reporta el RGB en vivo (circuito 6CynuRekrD2); ningun otro tipo
    # entra aqui, asi que no afecta a LED/resistencia/etc.
    "led-rgb-common-cathode": {
        "Red": "red",
        "Green": "green",
        "Blue": "blue",
        "Cathode": "cathode",
        "terminal-red": "red",
        "terminal-green": "green",
        "terminal-blue": "blue",
        "terminal-cathode": "cathode",
        "Terminal Red": "red",
        "Terminal Green": "green",
        "Terminal Blue": "blue",
        "Terminal Cathode": "cathode",
    },
}

_HOLE_RE = re.compile(r"^([a-j])(\d+)$")
_HOLE_REVERSED_RE = re.compile(r"^(\d+)([a-j])$")
_RAIL_RE = re.compile(r"^([a-z])(\d+)$")
_LOW_ROWS = frozenset("abcde")


def _slug(raw_type):
    return str(raw_type).strip().lower().replace(" ", "-").replace("_", "-")


def _canonical_type(raw_type):
    if not isinstance(raw_type, str) or not raw_type.strip():
        return None
    canonical = fixture_type(raw_type)
    if canonical is not None:
        return canonical
    return _slug(raw_type)


def _is_breadboard(canonical, raw_type):
    if canonical == "breadboard":
        return True
    return isinstance(raw_type, str) and "breadboard" in raw_type.casefold()


def _normalize_pin(pin, canonical):
    by_type = _PIN_ALIASES_BY_TYPE.get(canonical)
    if by_type is not None and pin in by_type:
        return by_type[pin]
    if pin in _PIN_ALIASES:
        return _PIN_ALIASES[pin]
    # Supuesto: en los wires el Uno reporta "GND", pero en components y en
    # las fixtures el pin se llama "GND1". Solo aplica al Arduino Uno.
    if canonical == "arduino-uno":
        return "GND1" if pin == "GND" else pin
    # Alias genéricos seguros en componentes no-Uno (p. ej. TMP36 reporta
    # "Power"/"GND" y su fixture usa vcc/gnd). Resistor/LED no usan estos
    # nombres, por lo que no se ven afectados.
    if pin == "Power":
        return "vcc"
    if pin == "GND":
        return "gnd"
    # El HC-SR04 en vivo se reporta como "Ultrasonic Distance Sensor
    # (4-pin)", que no resuelve a "ultrasonic-hcsr04": sus nombres
    # Trigger/Echo/Ground son inequivocos y ningun Uno/resistencia/LED
    # los usa, asi que el alias generico es seguro para esos tipos.
    if canonical not in ("arduino-uno", "resistor", "led"):
        if pin == "Ground":
            return "gnd"
        if pin == "Trigger":
            return "trig"
        if pin == "Echo":
            return "echo"
    return pin


class _UnionFind:
    def __init__(self):
        self._parent = {}

    def find(self, node):
        parent = self._parent.setdefault(node, node)
        if parent != node:
            self._parent[node] = self.find(parent)
        return self._parent[node]

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[rb] = ra


def derive_nets(inspect_data: dict) -> list[list[str]]:
    inspect_data = inspect_data or {}
    components = inspect_data.get("components") or []
    wires = inspect_data.get("wires") or []

    counters = {}

    def _assign_ref(canonical):
        if canonical == "arduino-uno":
            counters[canonical] = counters.get(canonical, 0) + 1
            n = counters[canonical]
            return "uno" if n == 1 else f"uno{n}"
        prefix = _REF_PREFIX.get(canonical, (canonical or "comp").replace("-", ""))
        counters[prefix] = counters.get(prefix, 0) + 1
        return f"{prefix}{counters[prefix]}"

    # instance_id -> (ref, canonical, is_breadboard)
    by_instance = {}
    breadboard_instances = set()
    for comp in components:
        if not isinstance(comp, dict):
            continue
        raw_type = comp.get("type")
        canonical = _canonical_type(raw_type)
        if canonical is None:
            continue
        is_bb = _is_breadboard(canonical, raw_type)
        ref = None if is_bb else _assign_ref(canonical)
        instance_id = comp.get("instance_id")
        if instance_id:
            by_instance[instance_id] = (ref, canonical, is_bb)
            if is_bb:
                breadboard_instances.add(instance_id)

    def _resolve(endpoint):
        """Devuelve (nodo, es_real) o None si el endpoint no es usable."""
        if not isinstance(endpoint, dict):
            return None
        pin = endpoint.get("pin")
        if pin is None or (isinstance(pin, str) and not pin.strip()):
            return None
        pin = str(pin).strip()

        instance_id = endpoint.get("instance_id")
        component = endpoint.get("component")

        record = None
        if instance_id:
            record = by_instance.get(instance_id)
        elif component:
            record = by_instance.get(component)

        if record is None:
            return None

        ref, canonical, is_bb = record
        bb_key = instance_id or component

        if is_bb:
            lowered = pin.casefold()
            match = _HOLE_RE.match(lowered)
            row = column = None
            if match:
                row, column = match.group(1), match.group(2)
            else:
                match = _HOLE_REVERSED_RE.match(lowered)
                if match:
                    column, row = match.group(1), match.group(2)
            if row is not None:
                half = "low" if row in _LOW_ROWS else "high"
                return (("bb-col", bb_key, column, half), False)
            rail = _RAIL_RE.match(lowered)
            if rail:
                return (("bb-rail", bb_key, rail.group(1)), False)
            return (("bb-pin", bb_key, lowered), False)

        return (f"{ref}.{_normalize_pin(pin, canonical)}", True)

    uf = _UnionFind()
    real_nodes = set()
    for wire in wires:
        if not isinstance(wire, dict):
            continue
        source = _resolve(wire.get("source"))
        target = _resolve(wire.get("target"))
        if source is None or target is None:
            continue
        for node, is_real in (source, target):
            if is_real:
                real_nodes.add(node)
        uf.union(source[0], target[0])

    groups = {}
    for node in real_nodes:
        groups.setdefault(uf.find(node), set()).add(node)

    nets = [sorted(group) for group in groups.values() if len(group) >= 2]
    nets.sort()
    return nets
