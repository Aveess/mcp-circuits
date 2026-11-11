_TYPE_MAP = {
    "Arduino Uno R3": "arduino-uno",
    "LED": "led",
    "Resistor": "resistor",
}

_REF_PREFIX = {
    "led": "led",
    "resistor": "r",
}


def _slug(raw_type):
    return str(raw_type).strip().lower().replace(" ", "-").replace("_", "-")


def normalize_circuit(inspect_data: dict, schematic_data: dict) -> dict:
    inspect_data = inspect_data or {}
    schematic_data = schematic_data or {}

    components = []
    ref_by_component = {}
    counters = {}

    for comp in inspect_data.get("components") or []:
        if not isinstance(comp, dict):
            continue
        raw_type = comp.get("type", "")
        norm_type = _TYPE_MAP.get(raw_type, _slug(raw_type))

        if norm_type == "arduino-uno":
            counters[norm_type] = counters.get(norm_type, 0) + 1
            n = counters[norm_type]
            ref = "uno" if n == 1 else f"uno{n}"
        else:
            prefix = _REF_PREFIX.get(norm_type, norm_type.replace("-", ""))
            counters[prefix] = counters.get(prefix, 0) + 1
            ref = f"{prefix}{counters[prefix]}"

        components.append({"ref": ref, "type": norm_type})
        ref_by_component.setdefault(raw_type, ref)
        if comp.get("instance_id"):
            ref_by_component.setdefault(comp["instance_id"], ref)

    nets = []
    for net in schematic_data.get("nets") or []:
        if isinstance(net, dict):
            pins = net.get("pins") or []
        elif isinstance(net, list):
            pins = net
        else:
            continue
        endpoints = []
        for pin in pins:
            if not isinstance(pin, dict):
                continue
            ref = ref_by_component.get(pin.get("component"))
            if ref is None:
                continue
            endpoints.append(f"{ref}.{pin.get('pin')}")
        if len(endpoints) >= 2:
            nets.append(endpoints)

    return {"components": components, "nets": nets}
