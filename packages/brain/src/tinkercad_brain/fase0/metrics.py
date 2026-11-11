import statistics

_ERROR_MARKERS = ("error", "failed to compile", "compilation", "no compila")


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
                "median": statistics.median(values),
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
