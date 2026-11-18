from tinkercad_brain.fase0.metrics import latency_summary


def build_report(records: list[dict]) -> dict:
    failures = []
    samples: dict[str, list[float]] = {}

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise TypeError(
                f"record at index {index} must be a dict, "
                f"got {type(record).__name__}"
            )
        tool = record.get("tool") or "unknown"
        samples.setdefault(tool, []).append(record.get("elapsed_s", 0.0))
        if not record.get("ok", False):
            output = record.get("output")
            text = "" if output is None else str(output)
            failures.append({"tool": tool, "output": text[:200]})

    return {
        "total_calls": len(records),
        "failures": failures,
        "latency": latency_summary(samples),
        "tools_used": sorted(samples),
    }
