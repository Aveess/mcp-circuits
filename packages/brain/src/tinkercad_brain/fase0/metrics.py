import statistics

_ERROR_MARKERS = ("error", "failed to compile", "compilation", "no compila")

_GND_PINS = {"GND", "GND1", "GND2", "GND3"}
_OPAQUE_PREFIX = "__unpaired__:"


def _median(values):
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2:
        return ordered[mid]
    a, b = ordered[mid - 1], ordered[mid]
    return a + (b - a) / 2


def compare_circuits(expected, actual) -> dict:
    expected_components = expected.get("components", [])
    actual_by_ref = {c.get("ref"): c.get("type") for c in actual.get("components", [])}

    missing_components = sorted(
        c["ref"]
        for c in expected_components
        if actual_by_ref.get(c.get("ref")) != c.get("type")
    )
    actual_components_unique = {
        (c.get("ref"), c.get("type")) for c in actual.get("components", [])
    }
    correct_components = len(expected_components) - len(missing_components)
    denom_components = max(len(expected_components), len(actual_components_unique))
    components_score = correct_components / denom_components if denom_components else 1.0

    expected_nets = expected.get("nets", [])
    actual_net_sets = {frozenset(net) for net in actual.get("nets", [])}
    missing_nets = sorted(
        sorted(net) for net in expected_nets if frozenset(net) not in actual_net_sets
    )
    correct_nets = len(expected_nets) - len(missing_nets)
    actual_nets_unique = {tuple(net) for net in actual.get("nets", [])}
    denom_nets = max(len(expected_nets), len(actual_nets_unique))
    nets_score = correct_nets / denom_nets if denom_nets else 1.0

    return {
        "components_score": components_score,
        "nets_score": nets_score,
        "score": (components_score + nets_score) / 2,
        "missing_components": missing_components,
        "missing_nets": missing_nets,
    }


def _merged_groups(nets):
    """Fusiona nets que comparten endpoints; devuelve (grupos, endpoint->grupo)."""
    groups = []
    for net in nets:
        current = set(net)
        if not current:
            continue
        merged = []
        for group in groups:
            if group & current:
                current |= group
            else:
                merged.append(group)
        merged.append(current)
        groups = merged
    index = {}
    for i, group in enumerate(groups):
        for endpoint in group:
            index[endpoint] = i
    return groups, index


def compare_connectivity(expected: dict, actual: dict) -> dict:
    """Compara por equivalencia electrica, no por igualdad literal de nets.

    Alinea componentes por (type, orden entre los del mismo type) y traduce
    las nets de actual al espacio de refs esperadas. Dos endpoints estan
    conectados si quedan en la misma net tras fusionar las nets que se
    solapan (p. ej. una tierra comun leida como una sola net equivale a
    varias nets esperadas que comparten ``uno.GND1``).

    Un corto es grave: si hay pares conectados en actual que pertenecen a
    grupos esperados distintos, ``score`` se multiplica por 0.5.
    """
    expected_components = expected.get("components", []) or []
    actual_components = actual.get("components", []) or []

    expected_by_type = {}
    for comp in expected_components:
        expected_by_type.setdefault(comp.get("type"), []).append(comp.get("ref"))

    # Mapeo ref_actual -> ref_expected por orden dentro de cada type.
    mapping = {}
    position_by_type = {}
    extra_components = []
    for comp in actual_components:
        comp_type = comp.get("type")
        pos = position_by_type.get(comp_type, 0)
        position_by_type[comp_type] = pos + 1
        candidates = expected_by_type.get(comp_type, [])
        if pos < len(candidates):
            mapping[comp.get("ref")] = candidates[pos]
        else:
            extra_components.append(comp.get("ref"))

    paired_expected = set(mapping.values())
    missing_components = sorted(
        c.get("ref") for c in expected_components if c.get("ref") not in paired_expected
    )
    correct = len(mapping)
    actual_unique = {(c.get("ref"), c.get("type")) for c in actual_components}
    denom = max(len(expected_components), len(actual_unique))
    components_score = correct / denom if denom else 1.0

    uno_refs = {"uno"}
    for comp in expected_components:
        if comp.get("type") == "arduino-uno" or comp.get("ref") == "uno":
            uno_refs.add(comp.get("ref"))
    if "uno" in mapping.values():
        uno_refs.add("uno")
    actual_type_by_ref = {c.get("ref"): c.get("type") for c in actual_components}

    def _canonical(endpoint):
        ref, dot, pin = str(endpoint).partition(".")
        if dot and ref in uno_refs and pin in _GND_PINS:
            return f"{ref}.GND1"
        return endpoint

    def _translate(endpoint):
        ref, dot, pin = str(endpoint).partition(".")
        if ref not in mapping:
            opaque = str(endpoint)
            if dot and pin in _GND_PINS and (
                ref == "uno" or actual_type_by_ref.get(ref) == "arduino-uno"
            ):
                opaque = f"{ref}.GND1"
            return f"{_OPAQUE_PREFIX}{opaque}"
        translated = f"{mapping[ref]}.{pin}" if dot else mapping[ref]
        return _canonical(translated)

    translated_nets = []
    for net in actual.get("nets", []) or []:
        translated = [_translate(ep) for ep in net]
        if translated:
            translated_nets.append(translated)

    actual_groups, actual_group_of = _merged_groups(translated_nets)
    expected_nets = [
        [_canonical(ep) for ep in net] for net in (expected.get("nets", []) or [])
    ]
    _, expected_group_of = _merged_groups(expected_nets)
    if expected_nets:
        connected = 0
        for net in expected_nets:
            endpoints = list(dict.fromkeys(net))
            if len(endpoints) <= 1:
                connected += 1
            elif all(ep in actual_group_of for ep in endpoints) and len(
                {actual_group_of[ep] for ep in endpoints}
            ) == 1:
                connected += 1
        connectivity_score = connected / len(expected_nets)
    else:
        connectivity_score = 1.0

    shorts = []
    for group in actual_groups:
        ordered = sorted(group)
        for i, a in enumerate(ordered):
            for b in ordered[i + 1:]:
                if (
                    a in expected_group_of
                    and b in expected_group_of
                    and expected_group_of[a] != expected_group_of[b]
                ):
                    shorts.append([a, b])
    shorts.sort()

    score = (components_score + connectivity_score) / 2
    if shorts:
        score *= 0.5

    return {
        "score": score,
        "components_score": components_score,
        "connectivity_score": connectivity_score,
        "shorts": shorts,
        "missing_components": missing_components,
        "extra_components": sorted(extra_components),
    }


def latency_summary(samples: dict[str, list[float]]) -> dict:
    summary = {}
    for tool, values in samples.items():
        if any(v < 0 for v in values):
            raise ValueError(f"negative latency sample for {tool!r}")
        if not values:
            summary[tool] = {"n": 0, "median": 0.0, "worst": 0.0, "mean": 0.0}
        else:
            summary[tool] = {
                "n": len(values),
                "median": _median(values),
                "worst": max(values),
                "mean": statistics.mean(values),
            }
    return summary


_SUCCESS_PHRASES = ("0 errors", "no errors", "sin errores")
_SUCCESS_WORDS = ("finished", "success", "succeeded", "completed", "ok")


def _has_error(text: str) -> bool:
    cleaned = text
    for phrase in _SUCCESS_PHRASES:
        cleaned = cleaned.replace(phrase, "")
    for marker in _ERROR_MARKERS:
        if marker not in cleaned:
            continue
        if marker == "compilation" and any(w in cleaned for w in _SUCCESS_WORDS):
            continue
        return True
    return False


def classify_compile_result(status_text, serial_text) -> str:
    status = (status_text or "").lower()
    serial = (serial_text or "").lower()
    if _has_error(status) or _has_error(serial):
        return "compile_error"
    if "running" in status or "simul" in status:
        return "running"
    return "unknown"
