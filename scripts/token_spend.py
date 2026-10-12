#!/usr/bin/env python3
"""Total Claude Code tokens from local session logs -> data/tokens.json.

Run on your Mac (the logs live in ~/.claude/projects), then commit data/tokens.json.
Only the total and two dates are written; no prompts or project names leave the machine.
"""
import datetime as dt
import json
from pathlib import Path

LOGS = Path.home() / ".claude/projects"
OUT = Path(__file__).resolve().parent.parent / "data/tokens.json"
FIELDS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def main():
    seen, total, first = set(), 0, None
    for f in LOGS.rglob("*.jsonl"):
        for line in f.open(errors="ignore"):
            if '"usage"' not in line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            msg = row.get("message") or {}
            usage = msg.get("usage")
            key = (msg.get("id"), row.get("requestId"))
            if not usage or key in seen:  # streamed messages repeat the same usage block
                continue
            seen.add(key)
            total += sum(usage.get(k) or 0 for k in FIELDS)
            ts = row.get("timestamp", "")[:10]
            if ts and (first is None or ts < first):
                first = ts
    prev = json.loads(OUT.read_text()) if OUT.exists() else {}
    data = {
        # logs get pruned over time, so never let the published number go backwards
        "total": max(total, prev.get("total", 0)),
        "since": min(filter(None, [first, prev.get("since")]), default=dt.date.today().isoformat()),
        "synced": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }
    OUT.write_text(json.dumps(data, indent=2) + "\n")
    print(f"{data['total']:,} tokens since {data['since']}")


if __name__ == "__main__":
    main()
