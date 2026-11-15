"""Generador de la fixture `contador-0-7-jk-v2` (taller 3, puntos 5 y 6).

Mismo sistema que `contador-0-7-jk` y misma tabla de verdad, con dos cambios
que Eddie aprobo y que hacen el armado legible:

- el decodificador se construye con **AND/OR/NOT/XOR reales** (las expresiones
  del punto 4 tal como estan escritas): 1 x 74HC04, 1 x 74HC86, 2 x 74HC08 y
  3 x 74HC32, siete integrados en vez de ocho;
- el display va en **catodo comun**, asi que la compuerta maneja el segmento
  directo a traves de su resistencia de 220 ohmios y el nodo que lee el sketch
  es la salida de la compuerta (positivo).

El dibujo es el de la v2: los siete integrados insertados en una breadboard
grande y los JK, el 555, el display y las resistencias en otra, con puentes de
hueco a hueco (ver ``layout_v2``).

Pines del Uno:
    D2   lectura del reloj (mide el periodo)
    D3   Q0        D4  Q1        D5  Q2
    D6   lectura de fg (el Uno R3 solo tiene A0..A5)
    D8   EN (salida)             D9  RESET (activo en alto, salida)
    A0..A5 lecturas de fa..ff
"""

from __future__ import annotations

from tinkercad_brain.decoder7 import (
    GATES_V2,
    SEGMENT_OUTPUT_V2,
    XOR_GATES_V2,
    signal_nets_v2,
)

__all__ = ["FIXTURE_ID", "contador_jk_v2_fixture"]

FIXTURE_ID = "contador-0-7-jk-v2"

# Segmento -> resistencia serie de 220 ohm.
_SERIES_REF = {"a": "ra", "b": "rb", "c": "rc", "d": "rd",
               "e": "re", "f": "rf", "g": "rg"}

# Segmento -> pin de lectura del Uno (A0..A5 y D6 para el septimo).
_SENSE_PIN = {"a": "A0", "b": "A1", "c": "A2", "d": "A3",
              "e": "A4", "f": "A5", "g": "D6"}

_CHIPS = sorted({gate.chip for gate in GATES_V2 + XOR_GATES_V2})

# Salida de compuerta que produce cada segmento (fa..fg), para no escribir a
# mano el chip y la ranura: sale del netlist del decodificador.
_SEGMENT_GATE = {
    gate.out: gate for gate in GATES_V2 if gate.out in SEGMENT_OUTPUT_V2.values()
}

# Entradas de compuerta que el diseno no usa. Una entrada CMOS no puede quedar
# flotando: va a GND. Sale del netlist, no de una lista escrita a mano.

_DOC = [
    "Taller 3 - Contador 0 a 7 con flip-flops JK (v2).",
    "",
    "Contador: tres flip-flops del 74HC73 en cascada. El 555 entrega el",
    "reloj (~1 Hz) al primero; Q0 relojea al segundo y Q1 al tercero.",
    "Q0 es el bit menos significativo. Los JK disparan en flanco de",
    "bajada, como pide el taller. R es activo en bajo: el inversor u1.6",
    "produce nR desde RESET.",
    "",
    "EN (D8) va a J y K de las tres etapas: con EN=1 basculan; con EN=0",
    "conservan el estado. RESET (D9, activo en alto) llega al inversor y",
    "de ahi a las tres R: vuelve a 000 sin esperar flanco.",
    "",
    "Decodificador (punto 4) con las expresiones del taller tal como",
    "estan escritas:",
    "  a = Q1 + NOT(Q2 XOR Q0)",
    "  b = NOT Q2 + NOT(Q1 XOR Q0)",
    "  c = Q2 + NOT Q1 + Q0",
    "  d = e + Q0(Q2 XOR Q1)",
    "  e = NOT Q0 (Q1 + NOT Q2)",
    "  f = NOT Q1 NOT Q0 + Q2(NOT Q1 + NOT Q0)",
    "  g = (Q2 XOR Q1) + Q1 NOT Q0",
    "",
    "Se arma con compuertas reales: 1 x 74HC04 (seis inversores), 1 x",
    "74HC86 (tres XOR), 2 x 74HC08 (AND) y 3 x 74HC32 (OR). Las entradas",
    "sobrantes de los integrados van a GND: una entrada CMOS nunca queda",
    "flotando.",
    "",
    "El display es de CATODO COMUN: los dos comunes a GND y cada segmento",
    "a la salida de su compuerta por una resistencia de 220 ohmios. Un",
    "segmento luce con HIGH, asi que el sketch lee el nodo de la compuerta",
    "tal cual (en la v1 habia un inversor y se leia LOW).",
    "",
    "Tabla (1 = segmento encendido, convencion del taller):",
    "  digito  Q2Q1Q0  a b c d e f g",
    "    0      000     1 1 1 1 1 1 0",
    "    1      001     0 1 1 0 0 0 0",
    "    2      010     1 1 0 1 1 0 1",
    "    3      011     1 1 1 1 0 0 1",
    "    4      100     0 1 1 0 0 1 1",
    "    5      101     1 0 1 1 0 1 1",
    "    6      110     1 0 1 1 1 1 1",
    "    7      111     1 1 1 0 0 0 0",
    "",
    "Pruebas del punto 5 que ejecuta el sketch:",
    "  1. RESET -> 000 y digito 0.",
    "  2. EN=1 -> dos ciclos completos 0..7..0..7..0.",
    "  3. EN=0 -> el numero se mantiene varios flancos; al volver EN a 1",
    "     continua desde ese valor.",
    "  4. RESET en un valor intermedio -> vuelve a 0.",
    "Cada lectura se valida con una guarda: se lee Q, luego los segmentos",
    "y otra vez Q; si Q cambio en medio, el flanco del acarreo asincrono",
    "cayo dentro de la muestra y se descarta. La muestra valida se",
    "re-comprueba 5 ms despues antes de comparar con la tabla.",
]

_ORACLE = [
    "El serial demuestra el sistema completo, no solo el conteo:",
    "  TEST:PERIODO=<ms>  periodo medido del reloj 555 en D2.",
    "  TEST:RESET=OK      tras RESET el contador esta en 000.",
    "  TEST:CICLO=OK      dos vueltas 0..7..0..7..0 con EN=1.",
    "  TEST:EN0=OK        con EN=0 el valor no cambia en tres periodos.",
    "  TEST:REANUDA=OK    al volver EN a 1 sigue desde el detenido.",
    "  TEST:RESET_MEDIO=OK RESET en un valor intermedio da 000.",
    "  TEST:DECODER=OK    cada lectura estable coincide con la tabla.",
    "  TEST:FIN=OK        la secuencia de pruebas termino.",
]

_NOTES = [
    "Interpretacion y diagnostico (punto 6):",
    "- La frecuencia del 555 es f = 1.44 / ((R1 + 2 R2) C). Con R1=10k,",
    "  R2=68k y C=10 uF da ~0.99 Hz. El valor real se mide en la",
    "  simulacion y se imprime en TEST:PERIODO.",
    "- Q0 conmuta a f/2, Q1 a f/4 y Q2 a f/8: cada etapa divide entre",
    "  dos. Por eso el numero cambia a la frecuencia del reloj pero cada",
    "  bit lo hace a la suya; el contador avanza un digito por flanco.",
    "- Si el display muestra valores intermedios al cambiar de digito es",
    "  el transitorio del acarreo asincrono: el bit bajo cambia antes que",
    "  el alto y la combinacion pasa por estados que no son el conteo. Se",
    "  lee el numero despues de que se propague, no en el flanco.",
    "- Si el conteo se repite 0,1,2,3 y vuelve a 0, Q2 nunca bascula:",
    "  revisar el reloj de la tercera etapa (Q1 -> CP de la tercera) y que",
    "  su R no este activa. El sintoma es de cableado del reloj, no del",
    "  decodificador.",
    "- Si un segmento queda siempre apagado o siempre encendido, el",
    "  problema esta en su compuerta o en su resistencia serie, no en el",
    "  contador: la tabla de verdad impresa permite comparar segmento por",
    "  segmento.",
    "- El display es de catodo comun: si se cablea como si fuera de",
    "  anodo, la mascara sale complementada y TEST:DECODER falla.",
]


def contador_jk_v2_fixture() -> dict:
    """Arma la fixture completa a partir del netlist v2 del decodificador."""
    components = [
        {"ref": "uno", "type": "arduino-uno"},
        {"ref": "t1", "type": "timer-555"},
        {"ref": "r1", "type": "resistor"},
        {"ref": "r2", "type": "resistor"},
        {"ref": "c1", "type": "capacitor"},
        {"ref": "c2", "type": "capacitor"},
        {"ref": "ff1", "type": "flip-flop-jk"},
        {"ref": "ff2", "type": "flip-flop-jk"},
        *({"ref": chip["chip"], "type": chip["type"]} for chip in _chip_types()),
        *({"ref": _SERIES_REF[seg], "type": "resistor"}
          for seg in SEGMENT_OUTPUT_V2),
        {"ref": "seg", "type": "seven-segment"},
    ]

    # --- Alimentacion -------------------------------------------------
    vcc = ["uno.5V", "t1.Vcc", "t1.Reset", "r1.1"]
    vcc += ["ff1.Vcc", "ff2.Vcc"] + [f"{chip}.Vcc" for chip in _CHIPS]

    # Catodo comun: los dos comunes del display van a GND.
    gnd = ["uno.GND1", "t1.GND", "c1.2", "c2.2", "ff1.GND", "ff2.GND",
           "seg.com1", "seg.com2"]
    gnd += [f"{chip}.GND" for chip in _CHIPS]
    # Mitad de ff1 sin usar: entradas a GND, nunca flotando. Y las compuertas
    # sobrantes de los integrados, por la misma razon.
    gnd += ["ff1.2J", "ff1.2K", "ff1.2CP", "ff1.2R"]
    gnd += _unused_gate_inputs()

    nets: list[list[str]] = [vcc, gnd]

    # --- Reloj 555 astable --------------------------------------------
    # R1 de Vcc a DIS; R2 de DIS a THR/TRIG; C1 de THR a GND; C2 en CTRL.
    nets += [
        ["r1.2", "r2.1", "t1.DIS"],
        ["r2.2", "t1.THR", "t1.TRIG", "c1.1"],
        ["t1.CTRL", "c2.1"],
    ]

    # --- Contador en cascada ------------------------------------------
    # El reloj tambien se lee en D2 para medir el periodo.
    nets.append(["t1.OUT", "ff1.1CP", "uno.D2"])

    # --- Decodificador -------------------------------------------------
    # signal_nets_v2 da una net por senal con su productor primero; aqui se
    # agregan los destinos que no son compuertas (lecturas y relojes).
    extra = {
        "Q0": ["ff2.1CP", "uno.D3"],
        "Q1": ["ff2.2CP", "uno.D4"],
        "Q2": ["uno.D5"],
    }
    producers = {
        "Q0": "ff1.1Q",
        "Q1": "ff2.1Q",
        "Q2": "ff2.2Q",
        "RESET": "uno.D9",
    }
    signal_by_node = {node: signal for signal, node in producers.items()}
    for net in signal_nets_v2(producers):
        nets.append(net + extra.get(signal_by_node.get(net[0]), []))

    # --- EN ------------------------------------------------------------
    nets.append(["uno.D8", "ff1.1J", "ff1.1K", "ff2.1J", "ff2.1K",
                 "ff2.2J", "ff2.2K"])

    # --- RESET ---------------------------------------------------------
    # El taller lo pide activo en alto; el 74HC73 lo tiene activo en bajo.
    # u1.6 invierte D9 y de ahi va a las tres R: una R al aire deja el
    # biestable en estado indefinido (medido en la v1: no pasaba de 3).
    nets.append(["u1.6Y", "ff1.1R", "ff2.1R", "ff2.2R"])

    # --- Segmentos: compuerta -> 220 ohm -> display, y lectura del nodo ---
    # Catodo comun: el segmento luce con HIGH, asi que quien lo maneja es la
    # salida positiva de la compuerta. La lectura va en ese mismo nodo (antes
    # de la resistencia): leer el pin del display daria la mascara al reves.
    #
    # Ojo: una salida que ya es net del decodificador (e = u2.1Y, que tambien
    # alimenta a d) es el MISMO nodo que el segmento. Si se declarara como net
    # aparte, la media columna quedaria con dos nets y el layout lo rechazaria
    # con razon: en la placa eso es un corto.
    net_de = {}
    for net in nets:
        for endpoint in net:
            net_de[endpoint] = net
    for seg in SEGMENT_OUTPUT_V2:
        gate = _SEGMENT_GATE[SEGMENT_OUTPUT_V2[seg]]
        salida = f"{gate.chip}.{gate.slot}Y"
        resistencia = f"{_SERIES_REF[seg]}.1"
        lectura = f"uno.{_SENSE_PIN[seg]}"
        if salida in net_de:
            net_de[salida].extend([resistencia, lectura])
        else:
            nets.append([salida, resistencia, lectura])
        nets.append([f"{_SERIES_REF[seg]}.2", f"seg.{seg}"])

    return {
        "id": FIXTURE_ID,
        "title": "Contador 0-7 v2: JK insertados, decodificador AND/OR/NOT/XOR",
        "layout": "v2",
        "boards": [
            {"kind": "large", "x": 870, "y": 0},
            {"kind": "large", "x": 1570, "y": 0},
        ],
        "components": components,
        "nets": nets,
        # Marcas del oraculo, en orden: el runner las busca como subcadena.
        "oracle_serial": [
            "TEST:PERIODO=",
            "TEST:RESET=OK",
            "TEST:CICLO=OK",
            "TEST:EN0=OK",
            "TEST:REANUDA=OK",
            "TEST:RESET_MEDIO=OK",
            "TEST:DECODER=OK",
            "TEST:FIN=OK",
        ],
        "sim_wait_seconds": 55,
        "code_features": ["pinMode", "digitalWrite", "digitalRead", "Serial"],
        "doc": _DOC,
        "oracle": _ORACLE,
        "notes": _NOTES,
    }


def _chip_types() -> list[dict]:
    """Los integrados del decodificador con su familia (``u1`` -> ``not-gate``)."""
    from tinkercad_brain.decoder7 import chip_type

    kind_by_chip: dict[str, str] = {}
    for gate in GATES_V2 + XOR_GATES_V2:
        kind_by_chip.setdefault(gate.chip, gate.kind)
    return [
        {"chip": chip, "type": chip_type(kind_by_chip[chip])}
        for chip in _CHIPS
    ]


def _unused_gate_inputs() -> list[str]:
    """Entradas de los integrados que nadie usa (se atan a GND).

    El 74HC04 tiene seis compuertas de **una** entrada, asi que sus ranuras
    van de 1 a 6 y solo existe ``A``; las demas familias son cuadruples de dos
    entradas (ranuras 1..4, ``A`` y ``B``).
    """
    used_slots = {(g.chip, g.slot) for g in GATES_V2 + XOR_GATES_V2}
    kind_by_chip: dict[str, str] = {}
    for gate in GATES_V2 + XOR_GATES_V2:
        kind_by_chip.setdefault(gate.chip, gate.kind)
    unused = []
    for chip in _CHIPS:
        single = kind_by_chip.get(chip) == "not"
        sides = ("A",) if single else ("A", "B")
        for slot in range(1, 7 if single else 5):
            if (chip, slot) in used_slots:
                continue
            unused += [f"{chip}.{slot}{side}" for side in sides]
    return unused
