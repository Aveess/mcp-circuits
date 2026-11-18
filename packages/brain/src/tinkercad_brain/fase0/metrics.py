import itertools
import math
import statistics

_ERROR_MARKERS = ("error", "failed to compile", "compilation", "no compila")

_GND_PINS = {"GND", "GND1", "GND2", "GND3"}
_OPAQUE_PREFIX = "__unpaired__:"

# Tope de combinaciones al alinear componentes del mismo type. Por encima de
# esto se usa solo el mapping posicional: preferimos un score conservador a
# explotar con un circuito de muchas partes iguales (8 resistencias = 40320).
_MAX_ALIGNMENT_COMBINATIONS = 5040


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


def _align_by_type(expected_components, actual_components):
    """Mapeo posicional ref_actual -> ref_esperada por type, mas los extras."""
    expected_by_type = {}
    for comp in expected_components:
        expected_by_type.setdefault(comp.get("type"), []).append(comp.get("ref"))

    mapping = {}
    extra_components = []
    used = set()
    pending = []
    for comp in actual_components:
        comp_type = comp.get("type")
        actual_ref = comp.get("ref")
        candidates = expected_by_type.get(comp_type, [])
        # El circuito bautizado trae la ref de la fixture como nombre: si
        # coincide, el emparejamiento es identidad y no hay nada que
        # permutar (con 8 resistencias la permutacion se sale del tope).
        if actual_ref is not None and actual_ref in candidates and actual_ref not in used:
            mapping[actual_ref] = actual_ref
            used.add(actual_ref)
        else:
            pending.append((actual_ref, comp_type))

    # Lo que no se emparejo por nombre toma el primer ref libre de su type,
    # en orden: el resto (si sobran partes de ese type) es extra. Sin esto
    # una parte extra del mismo tipo se comeria un ref ya usado y el extra
    # desaparecia del reporte (ronda 5).
    for actual_ref, comp_type in pending:
        free = [ref for ref in expected_by_type.get(comp_type, []) if ref not in used]
        if free:
            mapping[actual_ref] = free[0]
            used.add(free[0])
        else:
            extra_components.append(actual_ref)
    return mapping, extra_components, expected_by_type


def _aligned_candidates(mapping, expected_by_type, actual_components):
    """Mappings candidatos: el posicional y permutaciones dentro de cada type.

    Declarar dos resistencias en otro orden no cambia el cableado fisico, asi
    que el emparejamiento no puede depender de la posicion en el JSON: se
    permutan los refs esperados de cada type con 2+ componentes por lado.

    El coste es el producto de los factoriales de esos grupos; si supera
    ``_MAX_ALIGNMENT_COMBINATIONS`` se devuelve solo el mapping posicional
    para no explotar con circuitos de muchas partes iguales.
    """
    yield mapping

    paired_by_type = {}
    for comp in actual_components:
        ref = comp.get("ref")
        if ref in mapping:
            paired_by_type.setdefault(comp.get("type"), []).append(ref)

    groups = []
    combinations = 1
    for comp_type, actual_refs in paired_by_type.items():
        expected_refs = expected_by_type.get(comp_type, [])
        if len(actual_refs) < 2 or len(expected_refs) < 2:
            continue
        assigned = expected_refs[: len(actual_refs)]
        groups.append((actual_refs, assigned))
        combinations *= math.factorial(len(assigned))

    if not groups or combinations > _MAX_ALIGNMENT_COMBINATIONS:
        return

    perms = [list(itertools.permutations(assigned)) for _, assigned in groups]
    for combo in itertools.product(*perms):
        candidate = dict(mapping)
        for (actual_refs, _), perm in zip(groups, combo):
            for actual_ref, expected_ref in zip(actual_refs, perm):
                candidate[actual_ref] = expected_ref
        if candidate == mapping:
            continue
        yield candidate


def _alignment_rank(result: dict) -> tuple:
    """Ordena candidatos: mas nets conectadas, menos shorts, mejor components.

    ``connectivity_score`` es ``conectadas / len(expected_nets)``, asi que con
    el denominador fijo ordenar por el ratio equivale a ordenar por conteo.
    """
    return (
        result["connectivity_score"],
        -len(result["shorts"]),
        result["components_score"],
    )


def _score_mapping(mapping, expected, actual, extra_components) -> dict:
    """Traduce las nets de actual con ``mapping`` y calcula el resultado."""
    expected_components = expected.get("components", []) or []
    actual_components = actual.get("components", []) or []
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


def compare_connectivity(expected: dict, actual: dict) -> dict:
    """Compara por equivalencia electrica, no por igualdad literal de nets.

    Alinea componentes por type y traduce las nets de actual al espacio de
    refs esperadas. Dentro de un mismo type la alineacion es independiente
    del orden de declaracion: se prueban las permutaciones de los refs
    esperados y gana la que mas nets esperadas conecta, luego la que menos
    shorts produce, luego la de mejor ``components_score``; en empate se
    queda el mapping posicional. Dos endpoints estan conectados si quedan
    en la misma net tras fusionar las nets que se solapan (p. ej. una tierra
    comun leida como una sola net equivale a varias nets esperadas que
    comparten ``uno.GND1``).

    Un corto es grave: si hay pares conectados en actual que pertenecen a
    grupos esperados distintos, ``score`` se multiplica por 0.5.
    """
    expected_components = expected.get("components", []) or []
    actual_components = actual.get("components", []) or []

    mapping, extra_components, expected_by_type = _align_by_type(
        expected_components, actual_components
    )

    best = None
    for candidate in _aligned_candidates(
        mapping, expected_by_type, actual_components
    ):
        result = _score_mapping(candidate, expected, actual, extra_components)
        if best is None or _alignment_rank(result) > _alignment_rank(best):
            best = result
    return best


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
