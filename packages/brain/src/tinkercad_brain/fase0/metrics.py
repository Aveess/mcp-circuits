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
    if expected_components:
        components_score = (len(expected_components) - len(missing_components)) / len(
            expected_components
        )
    else:
        components_score = 1.0

    expected_nets = expected.get("nets", [])
    actual_net_sets = {frozenset(net) for net in actual.get("nets", [])}
    missing_nets = sorted(
        sorted(net) for net in expected_nets if frozenset(net) not in actual_net_sets
    )
    if expected_nets:
        nets_score = (len(expected_nets) - len(missing_nets)) / len(expected_nets)
    else:
        nets_score = 1.0

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


def classify_compile_result(status_text, serial_text) -> str:
    status = (status_text or "").lower()
    serial = (serial_text or "").lower()
    if any(marker in status or marker in serial for marker in _ERROR_MARKERS):
        return "compile_error"
    if "running" in status or "simul" in status:
        return "running"
    return "unknown"
