from tinkercad_brain.fase0.component_map import fixture_type

_REF_PREFIX = {
    "led": "led",
    "resistor": "r",
}


def _slug(raw_type):
    return str(raw_type).strip().lower().replace(" ", "-").replace("_", "-")


def _canonical_type(raw_type):
    canonical = fixture_type(raw_type)
    if canonical is not None:
        return canonical
    return _slug(raw_type)


def normalize_circuit(inspect_data: dict, schematic_data: dict) -> dict:
    inspect_data = inspect_data or {}
    schematic_data = schematic_data or {}

    components = []
    ref_by_instance_id = {}
    # Groups of refs sharing the same raw (Tinkercad) type name, in order.
    type_groups = []  # list of {"raw": str, "canonical": str, "refs": [str]}
    group_by_raw = {}
    counters = {}

    for comp in inspect_data.get("components") or []:
        if not isinstance(comp, dict):
            continue
        raw_type = comp.get("type")
        if not isinstance(raw_type, str) or not raw_type.strip():
            continue
        norm_type = _canonical_type(raw_type)

        if norm_type == "breadboard":
            continue

        if norm_type == "arduino-uno":
            counters[norm_type] = counters.get(norm_type, 0) + 1
            n = counters[norm_type]
            ref = "uno" if n == 1 else f"uno{n}"
        else:
            prefix = _REF_PREFIX.get(norm_type, norm_type.replace("-", ""))
            counters[prefix] = counters.get(prefix, 0) + 1
            ref = f"{prefix}{counters[prefix]}"

        components.append({"ref": ref, "type": norm_type})

        instance_id = comp.get("instance_id")
        if instance_id:
            ref_by_instance_id.setdefault(instance_id, ref)

        group = group_by_raw.get(raw_type)
        if group is None:
            group = {"raw": raw_type, "canonical": norm_type, "refs": []}
            group_by_raw[raw_type] = group
            type_groups.append(group)
        group["refs"].append(ref)

    def _find_group(name):
        if not isinstance(name, str):
            return None
        for group in type_groups:
            if name == group["raw"] or name == group["canonical"]:
                return group
            if name.strip().casefold() == " ".join(group["raw"].split()).casefold():
                return group
        return None

    # Pointer for round-robin assignment when a pin references a type
    # name shared by several components and carries no instance_id.
    type_pointer = {}

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
            pin_name = pin.get("pin")
            if pin_name is None or (isinstance(pin_name, str) and not pin_name.strip()):
                continue

            ref = None
            # Exact instance identification takes priority: either an
            # explicit instance_id field on the pin, or the component
            # field itself carrying the instance_id.
            pin_instance = pin.get("instance_id")
            if pin_instance and pin_instance in ref_by_instance_id:
                ref = ref_by_instance_id[pin_instance]
            else:
                component_key = pin.get("component")
                if component_key and component_key in ref_by_instance_id:
                    ref = ref_by_instance_id[component_key]
                elif component_key is not None:
                    group = _find_group(component_key)
                    if group is not None:
                        refs = group["refs"]
                        if len(refs) == 1:
                            ref = refs[0]
                        else:
                            idx = type_pointer.get(group["raw"], 0)
                            ref = refs[idx % len(refs)]
                            type_pointer[group["raw"]] = idx + 1
            if ref is None:
                continue
            endpoints.append(f"{ref}.{pin_name}")
        if len(endpoints) >= 2:
            nets.append(endpoints)

    return {"components": components, "nets": nets}
