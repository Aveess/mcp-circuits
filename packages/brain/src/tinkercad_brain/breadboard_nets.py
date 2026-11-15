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
    # Mismo criterio: normalize_circuit debe producir "lcd1" para que los
    # endpoints no queden opacos en compare_connectivity.
    "lcd-16x2": "lcd",
    # OJO: no agregar "photoresistor": "ldr". Los refs derivados deben
    # coincidir con los de normalize_circuit (photoresistor1), porque
    # compare_connectivity traduce refs por tipo+orden: un prefijo distinto
    # deja los endpoints como opacos y la conectividad cae en picada.
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
    # Acotado a lcd-16x2: los 16 terminales reales ya son los nombres de la
    # fixture (identidad). Se declaran explicitos para que el alias generico
    # "GND" -> "gnd" no rompa la net del LCD. Los cables del circuito real
    # cpySiVSE9vr, en cambio, etiquetan 8 pines con nombres humanos
    # (gnd, vcc, Contrast, Register Select, Read/Write, Enable, LED Anode,
    # LED Cathode): se mapean al nombre de inspect_circuit. DB0..DB7 son
    # identicos en ambos lados.
    "lcd-16x2": {
        "GND": "GND", "VDD": "VDD", "VO": "VO", "RS": "RS", "RW": "RW",
        "E": "E", "DB0": "DB0", "DB1": "DB1", "DB2": "DB2", "DB3": "DB3",
        "DB4": "DB4", "DB5": "DB5", "DB6": "DB6", "DB7": "DB7",
        "LED+": "LED+", "LED-": "LED-",
        "gnd": "GND",
        "vcc": "VDD",
        # Las patas de insercion al protoboard se etiquetan "Ground" y
        # "Power" (insert wires del circuito cpySiVSE9vr); sin estas dos
        # entradas caen al alias generico y salen como gnd/vcc.
        "Ground": "GND",
        "Power": "VDD",
        "Contrast": "VO",
        "Register Select": "RS",
        "Read/Write": "RW",
        "Enable": "E",
        "LED Anode": "LED+",
        "LED Cathode": "LED-",
    },
    # Display 7 segmentos (did 129710): inspect devuelve a..g, dp, com1,
    # com2 y el cableado guardado usa las etiquetas del DOM (A..G, DP,
    # Common). Se mapean ambas al nombre de la fixture.
    "seven-segment": {
        "A": "a", "B": "b", "C": "c", "D": "d", "E": "e", "F": "f", "G": "g",
        "DP": "dp",
        "Common": "com1",
        "Common 1": "com1",
        "Common 2": "com2",
    },
    # 74HC595 (did 116695): inspect devuelve Q0..Q7, DS, SHCP, STCP, OE, MR,
    # Vcc, GND; el cableado guardado usa nombres humanos. Q0 es "Output 1".
    "shift-register": {
        "Output 1": "Q0", "Output 2": "Q1", "Output 3": "Q2",
        "Output 4": "Q3", "Output 5": "Q4", "Output 6": "Q5",
        "Output 7": "Q6", "Output 8": "Q7",
        "Serial Out": "Q7S",
        "Input": "DS",
        "Shift Register Clock": "SHCP",
        "Output Register Clock": "STCP",
        "Output Enable": "OE",
        "Shift Register Clear": "MR",
        "Power": "Vcc",
        "Ground": "GND",
        "Vcc": "Vcc",
        "VCC": "Vcc",
        "GND": "GND",
    },
    # Compuertas logicas (74HC86 XOR, 74HC00 NAND): inspect devuelve 1A/1B/
    # 1Y, pero el cableado guardado etiqueta "Input 1A", "Input 1B" y
    # "Output 1". Power/Ground van a Vcc/GND con mayuscula (el alias
    # generico los dejaria en vcc/gnd y romperia la net).
    "xor-gate": {
        "Power": "Vcc",
        "Ground": "GND",
        "Input 1A": "1A", "Input 1B": "1B", "Output 1": "1Y",
        "Input 2A": "2A", "Input 2B": "2B", "Output 2": "2Y",
        "Input 3A": "3A", "Input 3B": "3B", "Output 3": "3Y",
        "Input 4A": "4A", "Input 4B": "4B", "Output 4": "4Y",
    },
    "nand-gate": {
        "Power": "Vcc",
        "Ground": "GND",
        "Input 1A": "1A", "Input 1B": "1B", "Output 1": "1Y",
        "Input 2A": "2A", "Input 2B": "2B", "Output 2": "2Y",
        "Input 3A": "3A", "Input 3B": "3B", "Output 3": "3Y",
        "Input 4A": "4A", "Input 4B": "4B", "Output 4": "4Y",
    },
    # 74HC74 (descubierto en vivo en euU4CI6HwhX): inspect devuelve
    # 1D/1CP/1RD/1SD/1Q/1NQ, pero el cableado guardado usa nombres humanos:
    # "Input 1", "Clock 1", "Reset 1", "Set 1", "Output 1" y
    # "Inverted Output 1". Power/Ground van a Vcc/GND con mayuscula.
    "flip-flop-d": {
        "Power": "Vcc",
        "Ground": "GND",
        "Input 1": "1D", "Clock 1": "1CP", "Reset 1": "1RD",
        "Set 1": "1SD", "Output 1": "1Q", "Inverted Output 1": "1NQ",
        "Input 2": "2D", "Clock 2": "2CP", "Reset 2": "2RD",
        "Set 2": "2SD", "Output 2": "2Q", "Inverted Output 2": "2NQ",
    },
    # 74HC73 (medido en vivo el 2026-11-14, sonda con los 14 pines cableados):
    # el modelo nombra 1J/1K/1CP/1R/1Q/1NQ y el cableado guardado escribe
    # "J 1", "K 1", "Clock 1", "Reset 1", "Output 1", "Inverted Output 1".
    # Este chip no tiene preset: solo hay un pin de reset por mitad.
    "flip-flop-jk": {
        "Power": "Vcc",
        "Ground": "GND",
        "J 1": "1J", "K 1": "1K", "Clock 1": "1CP", "Reset 1": "1R",
        "Output 1": "1Q", "Inverted Output 1": "1NQ",
        "J 2": "2J", "K 2": "2K", "Clock 2": "2CP", "Reset 2": "2R",
        "Output 2": "2Q", "Inverted Output 2": "2NQ",
    },
    # 555 Timer (descubierto en vivo en abIk7XRpSR4): inspect devuelve
    # CTRL/Reset/OUT/THR/GND/DIS/TRIG/Vcc, pero el cableado guardado usa
    # "Power", "Reset", "Ground", "Discharge", "Threshold", "Trigger",
    # "Out" y "Control". Power/Ground van a Vcc/GND con mayuscula.
    "timer-555": {
        "Power": "Vcc",
        "Ground": "GND",
        "Reset": "Reset",
        "Discharge": "DIS",
        "Threshold": "THR",
        "Trigger": "TRIG",
        "Out": "OUT",
        "Control": "CTRL",
        # Medido el 2026-11-14 en el contador 0-7: el mismo pin tambien se
        # guarda con el nombre completo y la fidelidad perdia esa net.
        "Control Voltage": "CTRL",
    },
    # Capacitor: inspect y guardado coinciden en "1"/"2"; "Terminal 1/2"
    # es lo que reportan los cables (canal compartido con el resistor).
    "capacitor": {
        "Terminal 1": "1",
        "Terminal 2": "2",
    },
    # 74HC93 (descubierto en vivo en fCB0eO8cBbn): inspect devuelve
    # CP0/CP1/MR1/MR2/Q0..Q3, pero el guardado usa "Clock 0", "Clock 1",
    # "Reset 1", "Reset 2" y "Output Bit 0".."Output Bit 3".
    "binary-counter": {
        "Power": "Vcc",
        "Ground": "GND",
        "Clock 0": "CP0",
        "Clock 1": "CP1",
        "Reset 1": "MR1",
        "Reset 2": "MR2",
        "Output Bit 0": "Q0",
        "Output Bit 1": "Q1",
        "Output Bit 2": "Q2",
        "Output Bit 3": "Q3",
    },
    # Relay SPDT (descubierto en vivo en bDUH17ymla2): inspect devuelve
    # COIL1/COIL2/COM1/COM2/R1/R2 pero el guardado usa "Terminal 1..12"
    # (numeracion fisica del componente: hay terminales de anclaje sin pin
    # logico). Medido cableando cada pin una sola vez.
    "relay-spdt": {
        "Terminal 8": "COIL1",
        "Terminal 5": "COIL2",
        "Terminal 12": "COM1",
        "Terminal 6": "R1",
        "Terminal 1": "COM2",
        "Terminal 7": "R2",
    },
    # Bombilla: dos terminales, el guardado los numera.
    "light-bulb": {"Terminal 1": "1", "Terminal 2": "2"},
    # PIR (descubierto en vivo en 9mlXTR2qKBd): el guardado usa
    # Signal/Power/Ground, inspect devuelve out/vcc/gnd.
    "pir-sensor": {"Signal": "out", "Power": "vcc", "Ground": "gnd"},
    # Teclado 4x4 (medido en vivo en bOhGx6ENPnn): el guardado usa
    # "Row 1..4" / "Column 1..4", inspect devuelve row1../column1...
    "keypad-4x4": {
        **{f"Row {i}": f"row{i}" for i in range(1, 5)},
        **{f"Column {i}": f"column{i}" for i in range(1, 5)},
    },
    # 74HC4017 (descubierto en vivo en ij6ypc8wB5x): inspect devuelve
    # Q0..Q9/CP0/CP1n/MR, pero el guardado usa "Output 1".."Output 10"
    # (Q0 -> Output 1, Q4 -> Output 5), "Clock", "Clock Enable" y "Reset".
    "decade-counter": {
        "Power": "Vcc",
        "Ground": "GND",
        "Clock": "CP0",
        "Clock Enable": "CP1n",
        "Reset": "MR",
        **{f"Output {i + 1}": f"Q{i}" for i in range(10)},
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
    # Match exacto a proposito: el guardado de Tinkercad emite etiquetas
    # fijas ("Output 1", "Common") y no se quiere inferir un pin que el
    # componente no declaro solo porque cambie la caja.
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


# Nombre de instancia valido como ref: una letra inicial y sin espacios ni
# signos. Los nombres automaticos de Tinkercad ("1", "3" en las placas) no
# pasan el filtro y siguen usando el contador posicional.
_REF_NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*$")


def preferred_refs(components, refs_by_name=None) -> dict:
    """{instance_id: ref} a partir del nombre que el puente dejo en cada parte.

    Dos fuentes, en este orden:

    1. ``refs_by_name`` ({nombre real en el documento: ref de la fixture}),
       que el build devuelve en ``placed[*].name``. Es la buena: Tinkercad
       deduplica los nombres (``setName("r2")`` con otro "r2" en el
       documento deja "r21"), asi que el unico que sabe que nombre quedo es
       el build. Sin este mapa, ocho resistencias iguales caen al mapping
       posicional y un orden de creacion distinto se lee como cortos que no
       existen (fase 39).
    2. El nombre del inspect, si TODAS las partes traen uno unico con forma
       de ref. Sirve para circuitos viejos, donde el nombre no colisionaba.

    Se devuelve ``{}`` (y todo sigue por contador) si la informacion no
    alcanza. El Uno y las placas quedan fuera de la regla: su nombre
    automatico no es una ref de la fixture.
    """
    if refs_by_name:
        mapping = {}
        for comp in components or []:
            if not isinstance(comp, dict):
                continue
            raw_type = comp.get("type")
            canonical = _canonical_type(raw_type)
            if canonical is None or canonical == "arduino-uno":
                continue
            if _is_breadboard(canonical, raw_type):
                continue
            name = comp.get("name")
            instance_id = comp.get("instance_id")
            if not isinstance(name, str) or not instance_id:
                return {}
            ref = refs_by_name.get(name.strip())
            if ref is None:
                return {}
            mapping[instance_id] = ref
        return mapping

    mapping = {}
    seen = set()
    for comp in components or []:
        if not isinstance(comp, dict):
            continue
        raw_type = comp.get("type")
        canonical = _canonical_type(raw_type)
        if canonical is None or canonical == "arduino-uno":
            continue
        if _is_breadboard(canonical, raw_type):
            continue
        name = comp.get("name")
        if not isinstance(name, str) or not _REF_NAME_RE.match(name.strip()):
            return {}
        name = name.strip()
        if name in seen:
            return {}
        seen.add(name)
        instance_id = comp.get("instance_id")
        if not instance_id:
            return {}
        mapping[instance_id] = name
    return mapping


def derive_nets(inspect_data: dict, refs_by_name=None) -> list[list[str]]:
    inspect_data = inspect_data or {}
    components = inspect_data.get("components") or []
    wires = inspect_data.get("wires") or []

    named = preferred_refs(components, refs_by_name)
    counters = {}

    def _assign_ref(canonical, instance_id=None):
        if instance_id and instance_id in named:
            return named[instance_id]
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
        instance_id = comp.get("instance_id")
        ref = None if is_bb else _assign_ref(canonical, instance_id)
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
