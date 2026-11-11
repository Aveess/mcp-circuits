from tinkercad_brain.fase0.metrics import latency_summary


def build_report(records: list[dict]) -> dict:
    failures = []
    samples: dict[str, list[float]] = {}

    for record in records:
        tool = record.get("tool")
        samples.setdefault(tool, []).append(record.get("elapsed_s", 0.0))
        if not record.get("ok", False):
            failures.append(
                {"tool": tool, "output": (record.get("output") or "")[:200]}
            )

    return {
        "total_calls": len(records),
        "failures": failures,
        "latency": latency_summary(samples),
        "tools_used": sorted(samples),
    }
