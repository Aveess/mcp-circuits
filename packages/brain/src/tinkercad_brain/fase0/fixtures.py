import json
from pathlib import Path


def load_fixtures(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("fixtures: se esperaba una lista de circuitos")
    if len(data) < 10:
        raise ValueError(f"fixtures: se requieren al menos 10 circuitos, hay {len(data)}")
    seen = set()
    for circuit in data:
        cid = circuit.get("id")
        if not cid:
            raise ValueError("fixtures: circuito sin id")
        if cid in seen:
            raise ValueError(f"fixtures: id duplicado: {cid}")
        seen.add(cid)
        components = circuit.get("components") or []
        if not components:
            raise ValueError(f"fixtures: circuito {cid} sin components")
        nets = circuit.get("nets") or []
        if not nets:
            raise ValueError(f"fixtures: circuito {cid} sin nets")
        refs = {c.get("ref") for c in components}
        for net in nets:
            for endpoint in net:
                if not isinstance(endpoint, str) or "." not in endpoint:
                    raise ValueError(
                        f"fixtures: extremo de net sin formato ref.pin: {endpoint!r} (circuito {cid})"
                    )
                ref, _, pin = endpoint.partition(".")
                if not ref or not pin:
                    raise ValueError(
                        f"fixtures: extremo de net sin formato ref.pin: {endpoint!r} (circuito {cid})"
                    )
                if ref not in refs:
                    raise ValueError(
                        f"fixtures: extremo {endpoint!r} refiere a un ref no declarado "
                        f"en components (circuito {cid})"
                    )
    return data
