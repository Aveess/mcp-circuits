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
