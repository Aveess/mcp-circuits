"""Deterministic protoboard layout planner.

Assigns breadboard holes to components from a fixture circuit.
Board: columns 1-30, rows j-i-h-g-f above the gap, e-d-c-b-a below.
"""

BLOCK_WIDTH = 6
MAX_COLUMN = 30
# Blocks start at 1, 7, 13, 19: a block starting at 25 would need
# column 31 (start + BLOCK_WIDTH) as its end boundary, beyond the board.
LAST_BLOCK_START = 19


class LayoutError(Exception):
    """Raised when a fixture cannot be interpreted for layout."""


def _parse_endpoint(endpoint):
    if not isinstance(endpoint, str) or "." not in endpoint:
        return None, None
    ref, pin = endpoint.split(".", 1)
    return ref, pin


def _led_resistor_pairs(components, nets):
    type_by_ref = {c["ref"]: c["type"] for c in components}
    led_to_resistor = {}
    used_resistors = set()
    for net in nets or []:
        led_ref = None
        resistor_ref = None
        for endpoint in net:
            ref, pin = _parse_endpoint(endpoint)
            if ref is None:
                continue
            if type_by_ref.get(ref) == "led" and pin == "anode":
                led_ref = ref
            elif type_by_ref.get(ref) == "resistor" and pin in ("1", "2"):
                resistor_ref = ref
        if led_ref and resistor_ref:
            if led_ref not in led_to_resistor and resistor_ref not in used_resistors:
                led_to_resistor[led_ref] = resistor_ref
                used_resistors.add(resistor_ref)
    return led_to_resistor


def plan_layout(fixture: dict) -> dict:
    if not isinstance(fixture, dict):
        raise LayoutError("fixture must be a dict")
    components = fixture.get("components")
    if not isinstance(components, list):
        raise LayoutError("fixture must have a 'components' list")
    for component in components:
        if not isinstance(component, dict) or "ref" not in component or "type" not in component:
            raise LayoutError("each component must have 'ref' and 'type'")

    order = {c["ref"]: i for i, c in enumerate(components)}
    type_by_ref = {c["ref"]: c["type"] for c in components}
    led_to_resistor = _led_resistor_pairs(components, fixture.get("nets"))

    placements = {}
    unplaced = []

    # Block units: each LED with its series resistor, plus standalone
    # resistors. Ordered by first appearance of any member in the fixture.
    units = []
    paired_resistors = set(led_to_resistor.values())
    for component in components:
        ref, ctype = component["ref"], component["type"]
        if ctype == "led":
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

    # Pushbuttons cross the central gap, after the LED/resistor blocks.
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
        elif ctype not in ("led", "resistor"):
            unplaced.append(ref)

    unplaced.sort(key=lambda ref: order[ref])
    return {"placements": placements, "unplaced": unplaced}
