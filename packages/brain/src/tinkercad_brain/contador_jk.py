"""Generador de la fixture `contador-0-7-jk` (taller 3, puntos 5 y 6).

Sistema completo: reloj 555 astable, tres biestables JK en cascada, EN,
RESET asincrono, decodificador de 7 funciones hecho con compuertas y display
de 7 segmentos de anodo comun.

El cableado del decodificador sale de `decoder7.signal_nets`, no de una lista
escrita a mano: una sola fuente para el netlist, el cableado y la tabla de
verdad que verifica el sketch.

Pines del Uno:
    D2   lectura del reloj (mide el periodo)
    D3   Q0        D4  Q1        D5  Q2
    D6   lectura de ng (el Uno R3 solo tiene A0..A5: el plan decia A0..A6)
    D8   EN (salida)             D9  RESET (activo en alto, salida)
    A0..A5 lecturas de na..nf
"""

from __future__ import annotations

from tinkercad_brain.decoder7 import GATES, SEGMENT_OUTPUT, XOR_GATES, signal_nets

__all__ = ["FIXTURE_ID", "contador_jk_fixture"]

FIXTURE_ID = "contador-0-7-jk"

# Segmento -> resistencia serie de 220 ohm.
_SERIES_REF = {"a": "ra", "b": "rb", "c": "rc", "d": "rd",
               "e": "re", "f": "rf", "g": "rg"}

# Segmento -> pin de lectura del Uno (A0..A5 y D6 para el septimo).
_SENSE_PIN = {"a": "A0", "b": "A1", "c": "A2", "d": "A3",
              "e": "A4", "f": "A5", "g": "D6"}

_NAND_CHIPS = sorted({gate.chip for gate in GATES})
_XOR_CHIPS = sorted({gate.chip for gate in XOR_GATES})

_DOC = [
    "Taller 3 - Contador 0 a 7 con tres flip-flops JK.",
    "",
    "Contador: tres 74HC73 en cascada. El 555 entrega el reloj (~1 Hz) al",
    "primer JK; Q0 relojea al segundo y Q1 al tercero. Q0 es el bit menos",
    "significativo. Los JK disparan en flanco de bajada, igual que pide el",
    "taller. R de cada JK es activo en bajo: u5.4 lo invierte desde RESET.",
    "",
    "EN (D8) va a J y K de las tres etapas: con EN=1 basculan; con EN=0",
    "conservan el estado. RESET (D9, activo en alto) llega a u5.4 y de ahi a",
    "las tres R: vuelve a 000 sin esperar flanco.",
    "",
    "Decodificador (punto 4), expresiones del taller:",
    "  a = Q1 + NOT(Q2 XOR Q0)",
    "  b = NOT Q2 + NOT(Q1 XOR Q0)",
    "  c = Q2 + NOT Q1 + Q0",
    "  d = e + Q0(Q2 XOR Q1)",
    "  e = NOT Q0 (Q1 + NOT Q2)",
    "  f = NOT Q1 NOT Q0 + Q2(NOT Q1 + NOT Q0)",
    "  g = (Q2 XOR Q1) + Q1 NOT Q0",
    "",
    "Las siete salidas se construyen con 27 NAND de 2 entradas (7 x 74HC00)",
    "mas 3 XOR (1 x 74HC86). Cada salida se invierte otra vez (na..ng) porque",
    "el display es de anodo comun: un segmento luce cuando su pin va a LOW.",
    "El pin de la compuerta tambien se lee en A0..A5 y D6 para que el sketch",
    "compare el decodificador con la tabla de verdad.",
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
    "Cada lectura se toma con dos muestras iguales separadas 60 ms: el acarreo",
    "entre JK es asincrono y el display pasa por un transitorio.",
]

_ORACLE = [
    "El serial demuestra el sistema completo, no solo el conteo:",
    "  TEST:PERIODO=<ms>  periodo medido del reloj 555 en D2.",
    "  TEST:RESET=OK      tras RESET el contador esta en 000 y el display en 0.",
    "  TEST:CICLO=OK      dos vueltas completas 0..7..0..7..0 con EN=1.",
    "  TEST:EN0=OK        con EN=0 el valor no cambia en tres periodos.",
    "  TEST:REANUDA=OK    al volver EN a 1 continua desde el valor detenido.",
    "  TEST:RESET_MEDIO=OK RESET en un valor intermedio devuelve 000.",
    "  TEST:DECODER=OK    cada lectura estable coincide con la tabla de verdad.",
    "  TEST:FIN=OK        la secuencia de pruebas termino.",
]

_NOTES = [
    "Interpretacion y diagnostico (punto 6):",
    "- La frecuencia del 555 es f = 1.44 / ((R1 + 2 R2) C). Con R1 = 10k,",
    "  R2 = 68k y C = 10 uF da ~0.99 Hz. El valor real se mide en la",
    "  simulacion y se imprime en TEST:PERIODO.",
    "- Q0 conmuta a f/2, Q1 a f/4 y Q2 a f/8: cada etapa divide entre dos.",
    "  Por eso el numero cambia a la frecuencia del reloj pero cada bit lo",
    "  hace a la suya; el contador completo avanza un digito por flanco.",
    "- Si el display muestra valores intermedios al cambiar de digito es el",
    "  transitorio del acarreo asincrono: el bit bajo cambia antes que el",
    "  alto y la combinacion pasa por estados que no son el conteo. Se lee",
    "  el numero despues de que se propague, no en el instante del flanco.",
    "- Si el conteo se repite 0,1,2,3 y vuelve a 0, Q2 nunca bascula: revisar",
    "  el reloj de la tercera etapa (Q1 -> CP de la tercera) y que su R no",
    "  este activa. El sintoma es de cableado del reloj, no del decodificador.",
    "- Si un segmento queda siempre apagado o siempre encendido, el problema",
    "  esta en su compuerta o en su resistencia serie, no en el contador: la",
    "  tabla de verdad impresa permite comparar segmento por segmento.",
]


def contador_jk_fixture() -> dict:
    """Arma la fixture completa a partir del netlist del decodificador."""
    components = [
        {"ref": "uno", "type": "arduino-uno"},
        {"ref": "t1", "type": "timer-555"},
        {"ref": "r1", "type": "resistor"},
        {"ref": "r2", "type": "resistor"},
        {"ref": "c1", "type": "capacitor"},
        {"ref": "c2", "type": "capacitor"},
        {"ref": "ff1", "type": "flip-flop-jk"},
        {"ref": "ff2", "type": "flip-flop-jk"},
        {"ref": "x1", "type": "xor-gate"},
        *({"ref": chip, "type": "nand-gate"} for chip in _NAND_CHIPS),
        *({"ref": _SERIES_REF[seg], "type": "resistor"}
          for seg in SEGMENT_OUTPUT),
        {"ref": "seg", "type": "seven-segment"},
    ]

    # --- Alimentacion -------------------------------------------------
    vcc = ["uno.5V", "t1.Vcc", "t1.Reset", "r1.1", "seg.com1"]
    vcc += ["ff1.Vcc", "ff2.Vcc", "x1.Vcc"] + [f"{c}.Vcc" for c in _NAND_CHIPS]

    gnd = ["uno.GND1", "t1.GND", "c1.2", "c2.2", "ff1.GND", "ff2.GND", "x1.GND"]
    gnd += [f"{c}.GND" for c in _NAND_CHIPS]
    # Mitades y compuertas sin usar: entradas CMOS a GND, nunca flotando.
    gnd += ["ff1.2J", "ff1.2K", "ff1.2CP", "ff1.2R", "u7.4A", "u7.4B",
            "x1.4A", "x1.4B"]

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
    # signal_nets da una net por senal con su productor primero; aqui se
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
    for net in signal_nets(producers):
        nets.append(net + extra.get(net[0], []))

    # --- EN ------------------------------------------------------------
    nets.append(["uno.D8", "ff1.1J", "ff1.1K", "ff2.1J", "ff2.1K",
                 "ff2.2J", "ff2.2K"])

    # --- Segmentos: compuerta -> 220 ohm -> display, y lectura del nodo
    for seg, gate_out in SEGMENT_OUTPUT.items():
        gate = next(g for g in GATES if g.out == gate_out)
        nets.append([f"{gate.chip}.{gate.slot}Y", f"{_SERIES_REF[seg]}.1",
                     f"uno.{_SENSE_PIN[seg]}"])
        nets.append([f"{_SERIES_REF[seg]}.2", f"seg.{seg}"])

    return {
        "id": FIXTURE_ID,
        "title": "Contador 0-7 con 3 JK, reloj 555 y decodificador de compuertas",
        "components": components,
        "nets": nets,
        # Las nueve resistencias no caben en una placa de 30 columnas (paso 6):
        # las siete de los segmentos van al banco de la segunda placa.
        "board2": [_SERIES_REF[seg] for seg in SEGMENT_OUTPUT],
        "wiring": "rails",
        "sim_wait_seconds": 55,
        "code_features": ["pinMode", "digitalWrite", "digitalRead", "Serial"],
        "doc": _DOC,
        "oracle": _ORACLE,
        "notes": _NOTES,
    }
