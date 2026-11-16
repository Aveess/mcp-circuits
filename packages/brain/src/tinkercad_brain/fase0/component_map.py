"""Mapa canónico de nombres de componentes ezhil/Tinkercad a slugs de fixtures."""

TYPE_MAP: dict[str, str] = {
    "Arduino Uno R3": "arduino-uno",
    "LED": "led",
    "Resistor": "resistor",
    "Pushbutton": "pushbutton",
    "Micro Servo": "servo",  # Supuesto: nombre visible del catálogo Tinkercad; ezhil exacto no verificado.
    "Potentiometer": "potentiometer",
    "Ultrasonic Distance Sensor": "ultrasonic-hcsr04",  # Supuesto: nombre visible del catálogo Tinkercad; ezhil exacto no verificado.
    "Ultrasonic Distance Sensor (4 Pin)": "ultrasonic-hcsr04",  # Verificado: nombre real ezhil en circuito 0W49xkaR18y (inspect_circuit).
    "Piezo": "buzzer",
    "Photoresistor": "photoresistor",
    "Photoresistor (LDR)": "photoresistor",  # Verificado: type real ezhil en circuito cZcqbZ3eNlA (inspect_circuit).
    "DC Motor": "dc-motor",  # Supuesto: nombre visible del catálogo Tinkercad; ezhil exacto no verificado.
    "Motor DC": "dc-motor",  # Supuesto: variante con orden inverso; ezhil exacto no verificado.
    "NPN Transistor": "transistor-npn",  # Verificado: type con pines collector/base/emitter; colocación en vivo OK (did 58468).
    "NPN Transistor (BJT)": "transistor-npn",  # Verificado: nombre real ezhil en circuito 73azwj2IJDE (inspect_circuit).
    "Transistor NPN": "transistor-npn",  # Supuesto: variante con orden inverso; ezhil exacto no verificado.
    "Transistor": "transistor-npn",  # Supuesto: nombre corto/genérico; ezhil exacto no verificado.
    "Diode": "diode",  # Supuesto: nombre visible del catálogo Tinkercad; ezhil exacto no verificado.
    "RGB LED": "led-rgb-common-cathode",
    "LED RGB": "led-rgb-common-cathode",  # Verificado: nombre real ezhil en circuito 6CynuRekrD2 (inspect_circuit).
    "TMP36": "tmp36",
    "Temperature Sensor [TMP36]": "tmp36",
    "Breadboard Small": "breadboard",  # Supuesto: nombre visible del catálogo Tinkercad; ezhil exacto no verificado.
    "H-bridge Motor Driver [L293D]": "l293d",  # Verificado: nombre real ezhil (inspect_circuit).
    "9V Battery": "battery-9v",  # Verificado: nombre real ezhil (inspect_circuit).
    "LCD 16 x 2": "lcd-16x2",  # Verificado: type real ezhil (did 113878, circuito ib98EAPoqPP).
    "7 Segment Display": "seven-segment",  # Verificado en vivo (did 129710, pines a..g, dp, com1, com2).
    "8-Bit Shift Register [74HC595]": "shift-register",  # Verificado en vivo (did 116695, pines Q0..Q7, DS, SHCP, STCP, OE, MR, Vcc, GND).
    "Shift Register": "shift-register",  # Alias del buscador del catalogo ("Shift Register" es lo que hay que pedir en add_component).
    "Quad XOR gate [74HC86]": "xor-gate",  # Verificado en vivo (did 116727, pines 1A..4A, 1B..4B, 1Y..4Y, Vcc, GND).
    "XOR Gate": "xor-gate",  # Alias del buscador (add_component acepta "XOR Gate").
    "Quad NAND gate [74HC00]": "nand-gate",  # Verificado en vivo (did 116696, pines 1A..4A, 1B..4B, 1Y..4Y, Vcc, GND).
    "Quad NAND gate": "nand-gate",  # Alias del buscador (add_component acepta "Quad NAND gate").
    # 74HC08/32/04 medidos en vivo el 2026-11-15 en la placa grande: inspect
    # reporta estos textos exactos (con el did entre corchetes).
    "Quad AND gate [74HC08]": "and-gate",  # did 116702, pines 1A..4A, 1B..4B, 1Y..4Y.
    "Quad OR gate [74HC32]": "or-gate",  # did 116721, mismos pines que el AND.
    "Hex Inverter [74HC04]": "not-gate",  # did 116701, seis compuertas 1A/1Y .. 6A/6Y.
    "Dual D Flip-Flop [74HC74]": "flip-flop-d",  # Verificado en vivo (did 116725, pines 1D/1CP/1RD/1SD/1Q/1NQ y la mitad 2).
    "D Flip-Flop": "flip-flop-d",  # Alias del buscador (add_component acepta "D Flip-Flop").
    "Dual J-K Flip-Flop [74HC73]": "flip-flop-jk",  # Verificado en vivo (did 116723, pines 1J/1K/1CP/1R/1Q/1NQ y la mitad 2).
    "555 Timer": "timer-555",  # Verificado en vivo (did 116689, pines CTRL/Reset/OUT/THR/GND/DIS/TRIG/Vcc).
    "Timer": "timer-555",  # Alias del buscador (add_component acepta "Timer").
    "Capacitor": "capacitor",  # Verificado en vivo (did 57752, terminales 1/2, propiedad "capacitance").
    "4-Bit Binary Counter [74HC93]": "binary-counter",  # Verificado en vivo (did 116728, CP0/CP1/MR1/MR2/Q0..Q3).
    "Binary Counter": "binary-counter",  # Alias del buscador (add_component acepta "Binary Counter").
    "Johnson Decade Counter [74HC4017]": "decade-counter",  # Verificado en vivo (did 129343, Q0..Q9, CP0, CP1n, MR).
    "Relay SPDT": "relay-spdt",  # Verificado en vivo (did 122167, 2 polos: COM1/R1 y COM2/R2).
    "Light bulb": "light-bulb",  # Verificado en vivo (did 116693, dos terminales).
    "PIR Sensor": "pir-sensor",  # Verificado en vivo (did 234203, out/vcc/gnd, cono de deteccion).
    # Verificado en vivo (did 203761): 4 filas + 4 columnas, sin alimentacion.
    "Keypad 4x4": "keypad-4x4",
    "Decade Counter": "decade-counter",  # Alias del buscador.
    # Fuente de la placa: el nombre que acepta el buscador del drawer medido en
    # vivo es "Power supply" (did 111724, pines Vcc/GND). El alias va primero
    # para que _TYPE_BY_SLUG conserve el nombre canonico.
    "Power Supply": "power-supply",
    "Power supply": "power-supply",
}


def _normalize(name: str) -> str:
    return " ".join(name.replace("-", " ").replace("_", " ").split()).casefold()


_NORMALIZED_MAP: dict[str, str] = {_normalize(name): slug for name, slug in TYPE_MAP.items()}


def fixture_type(ezhil_name: str) -> str | None:
    if not isinstance(ezhil_name, str):
        return None
    if ezhil_name in TYPE_MAP:
        return TYPE_MAP[ezhil_name]
    return _NORMALIZED_MAP.get(_normalize(ezhil_name))


def known_slugs() -> list[str]:
    return sorted(set(TYPE_MAP.values()))
