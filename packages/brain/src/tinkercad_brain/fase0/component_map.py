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
    "DC Motor": "dc-motor",
    "RGB LED": "led-rgb-common-cathode",
    "TMP36": "tmp36",
    "Temperature Sensor [TMP36]": "tmp36",
    "Breadboard Small": "breadboard",  # Supuesto: nombre visible del catálogo Tinkercad; ezhil exacto no verificado.
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
