"""Deterministic protoboard layout planner.

Assigns breadboard holes to components from a fixture circuit.
Board: columns 1-30, rows j-i-h-g-f above the gap, e-d-c-b-a below.
"""

BLOCK_WIDTH = 6
MAX_COLUMN = 30
# Blocks start at 1, 7, 13, 19: a block starting at 25 would need
# column 31 (start + BLOCK_WIDTH) as its end boundary, beyond the board.
LAST_BLOCK_START = 19
# First (leftmost) pin per 3-pin type, physical order left to right:
# servo gnd/vcc/signal, potentiometer 1/2/3, tmp36 vcc/vout/gnd.
THREE_PIN_FIRST_PIN = {"servo": "gnd", "potentiometer": "1", "tmp36": "vcc"}
THREE_PIN_PINS = 3
# Cursor advance per 3-pin block: 3 pin columns + 1 separation column.
THREE_PIN_WIDTH = 4
# HC-SR04 physical pin order left to right: vcc, trig, echo, gnd.
ULTRASONIC_PINS = 4
# Cursor advance per ultrasonic block: 4 pin columns + 1 separation column.
ULTRASONIC_WIDTH = 5


class LayoutError(Exception):
    """Raised when a fixture cannot be interpreted for layout."""


def _parse_endpoint(endpoint):
    if not isinstance(endpoint, str) or "." not in endpoint:
        return None, None
    ref, pin = endpoint.split(".", 1)
    return ref, pin


def _led_resistor_pairs(components, nets):
    if nets is not None and not isinstance(nets, list):
        raise LayoutError("fixture 'nets' must be a list")
    type_by_ref = {c["ref"]: c["type"] for c in components}
    led_to_resistor = {}
    leds_without_resistor = set()
    used_resistors = set()
    for net in nets or []:
        led_refs = []
        resistor_refs = []
        for endpoint in net:
            ref, pin = _parse_endpoint(endpoint)
            if ref is None:
                continue
            if type_by_ref.get(ref) == "led" and pin == "anode":
                if ref not in led_refs:
                    led_refs.append(ref)
            elif type_by_ref.get(ref) == "resistor" and pin in ("1", "2"):
                if ref not in resistor_refs:
                    resistor_refs.append(ref)
        for led_ref in led_refs:
            if led_ref in led_to_resistor:
                continue
            resistor_ref = next(
                (r for r in resistor_refs if r not in used_resistors), None
            )
            if resistor_ref is not None:
                led_to_resistor[led_ref] = resistor_ref
                used_resistors.add(resistor_ref)
                leds_without_resistor.discard(led_ref)
            elif resistor_refs:
                leds_without_resistor.add(led_ref)
    return led_to_resistor, leds_without_resistor


def plan_layout(fixture: dict) -> dict:
    if not isinstance(fixture, dict):
        raise LayoutError("fixture must be a dict")
    components = fixture.get("components")
    if not isinstance(components, list):
        raise LayoutError("fixture must have a 'components' list")
    for component in components:
        if not isinstance(component, dict) or "ref" not in component or "type" not in component:
            raise LayoutError("each component must have 'ref' and 'type'")
    seen_refs = set()
    for component in components:
        ref = component["ref"]
        if ref in seen_refs:
            raise LayoutError(f"duplicate component ref: {ref!r}")
        seen_refs.add(ref)
    nets = fixture.get("nets")
    if nets is not None and not isinstance(nets, list):
        raise LayoutError("fixture 'nets' must be a list")

    order = {c["ref"]: i for i, c in enumerate(components)}
    type_by_ref = {c["ref"]: c["type"] for c in components}
    led_to_resistor, leds_without_resistor = _led_resistor_pairs(components, nets)

    placements = {}
    unplaced = []

    # Block units: each LED with its series resistor, plus standalone
    # resistors. Ordered by first appearance of any member in the fixture.
    units = []
    paired_resistors = set(led_to_resistor.values())
    for component in components:
        ref, ctype = component["ref"], component["type"]
        if ctype == "led":
            if ref in leds_without_resistor:
                unplaced.append(ref)
                continue
            resistor = led_to_resistor.get(ref)
            members = [ref] + ([resistor] if resistor else [])
            units.append((min(order[m] for m in members), ref, resistor))
        elif ctype == "resistor" and ref not in paired_resistors:
            units.append((order[ref], None, ref))
    units.sort(key=lambda unit: unit[0])

    next_column = 1
    for _, led_ref, resistor_ref in units:
        if next_column > LAST_BLOCK_START:
            if resistor_ref:
                unplaced.append(resistor_ref)
            if led_ref:
                unplaced.append(led_ref)
            continue
        column = next_column
        next_column += BLOCK_WIDTH
        if resistor_ref:
            placements[resistor_ref] = {"at": f"{column}g", "pin": "1", "angle": 90}
        if led_ref:
            placements[led_ref] = {"at": f"{column + 4}i", "pin": "anode", "angle": 180}

    # Pushbuttons, 3-pin parts and the HC-SR04, after the LED/resistor
    # blocks. All share the next_column cursor (LED block: 6, pushbutton:
    # 1, 3-pin: 4, ultrasonic: 5), so no two blocks share a start column
    # or overlap in range.
    for component in components:
        ref, ctype = component["ref"], component["type"]
        if ctype == "arduino-uno" or ref in placements:
            continue
        if ctype == "pushbutton":
            if next_column > MAX_COLUMN:
                unplaced.append(ref)
            else:
                placements[ref] = {"at": f"{next_column}f", "pin": "1", "angle": 0}
                next_column += 1
        elif ctype in THREE_PIN_FIRST_PIN:
            if next_column + THREE_PIN_PINS - 1 > MAX_COLUMN:
                unplaced.append(ref)
            else:
                placements[ref] = {
                    "at": f"{next_column}c",
                    "pin": THREE_PIN_FIRST_PIN[ctype],
                    "angle": 0,
                }
                next_column += THREE_PIN_WIDTH
        elif ctype == "ultrasonic-hcsr04":
            if next_column + ULTRASONIC_PINS - 1 > MAX_COLUMN:
                unplaced.append(ref)
            else:
                placements[ref] = {
                    "at": f"{next_column}d",
                    "pin": "vcc",
                    "angle": 0,
                }
                next_column += ULTRASONIC_WIDTH
        elif ctype not in ("led", "resistor"):
            unplaced.append(ref)

    unplaced.sort(key=lambda ref: order[ref])
    return {"placements": placements, "unplaced": unplaced}
