import json
import time
from dataclasses import dataclass, field


@dataclass
class ProbeStep:
    tool: str
    arguments: dict = field(default_factory=dict)


@dataclass
class ProbeRecord:
    tool: str
    ok: bool
    elapsed_s: float
    output: str


def run_steps(steps, call_tool) -> list[ProbeRecord]:
    records: list[ProbeRecord] = []
    for step in steps:
        start = time.perf_counter()
        try:
            output = call_tool(step.tool, step.arguments)
            ok = True
        except Exception as exc:
            output = str(exc)
            ok = False
        elapsed_s = max(0.0, time.perf_counter() - start)
        records.append(
            ProbeRecord(tool=step.tool, ok=ok, elapsed_s=elapsed_s, output=output)
        )
    return records


def records_to_jsonl(records) -> str:
    lines = []
    for record in records:
        lines.append(
            json.dumps(
                {
                    "tool": record.tool,
                    "ok": record.ok,
                    "elapsed_s": record.elapsed_s,
                    "output": record.output,
                }
            )
        )
    return "".join(f"{line}\n" for line in lines)
