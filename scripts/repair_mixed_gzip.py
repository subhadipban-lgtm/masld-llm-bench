#!/usr/bin/env python3
"""Repair an archive whose gzip members were appended AFTER a truncation.

Scenario: a writer was killed mid-record, leaving a truncated gzip member.
A later resume appended new gzip members at the end of the file. The
platform's resilient reader streams the raw bytes through one decompressor
per member, but after a truncated member the appended members can become
unreachable, so the resumed records vanish from every read.

This script scans the raw bytes for every gzip member header (1f 8b 08),
decompresses each member on its own, keeps every complete JSON line, and
rewrites the archive as one clean gzip member. Deduplicates by
(task, sample) with last-record-wins to mirror load_indexed.

Usage:
  platform/.venv/bin/python scripts/repair_mixed_gzip.py <archive.jsonl.gz>
"""
from __future__ import annotations

import json
import sys
import zlib
from pathlib import Path

MAGIC = b"\x1f\x8b\x08"


def member_starts(raw: bytes) -> list[int]:
    """Offsets of every plausible gzip member header in the raw bytes."""
    starts: list[int] = []
    i = 0
    while True:
        j = raw.find(MAGIC, i)
        if j < 0:
            return starts
        starts.append(j)
        i = j + 1


def decompress_member(raw: bytes) -> tuple[str, bool]:
    """Decompress one member byte range; returns (text, complete?)."""
    dec = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        text = dec.decompress(raw).decode("utf-8", errors="replace")
    except zlib.error:
        return "", False
    return text, dec.eof


def recover(path: Path) -> list[dict]:
    raw = path.read_bytes()
    starts = member_starts(raw)
    if not starts:
        raise SystemExit(f"no gzip member header found in {path}")
    boundaries = starts[1:] + [len(raw)]
    records: list[dict] = []
    for s, e in zip(starts, boundaries):
        text, complete = decompress_member(raw[s:e])
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # partial tail line from the killed writer
        tag = "complete" if complete else "TRUNCATED"
        print(f"  member @{s}: {len(text.splitlines())} lines ({tag})")
    return records


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    path = Path(sys.argv[1])
    print(f"recovering {path} ({path.stat().st_size} bytes)...")
    records = recover(path)

    # Deduplicate by (task, sample), last record wins (archive convention).
    dedup: dict[tuple, dict] = {}
    n_meta = 0
    for r in records:
        if "__meta__" in r or "n_records" in r and "task" not in r:
            n_meta += 1
            continue
        if r.get("task") and r.get("sample"):
            dedup[(r["task"], r["sample"])] = r
    kept = list(dedup.values())
    print(f"recovered {len(records)} records ({n_meta} meta), "
          f"{len(kept)} unique (task, sample)")

    import gzip

    tmp = path.with_suffix(path.suffix + ".repaired")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp.replace(path)
    print(f"rewrote {path} as one clean member ({len(kept)} records)")


if __name__ == "__main__":
    main()
