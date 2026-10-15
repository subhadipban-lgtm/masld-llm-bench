"""Gzip-JSONL I/O for prompt corpora and evaluation archives.

Implements the research repositories' conventions exactly:

* optional ``__meta__`` JSON object as the first line;
* one JSON object per line, gzip-compressed;
* archives are append-only (resume support) and may be truncated when a
  writer is killed mid-record — :func:`read_jsonl_resilient` recovers every
  complete record from such files.

Checksums follow the manifest convention: first 16 hex characters of SHA-256.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import zlib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from masld_platform.guardrails import GuardrailError
from masld_platform.schemas import MetaHeader


def sha16(path: str | Path) -> str:
    """First 16 hex chars of the SHA-256 of a file (manifest convention)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def parse_meta(line_obj: dict[str, Any]) -> MetaHeader | None:
    """Return a :class:`MetaHeader` if the parsed line is a ``__meta__`` header.

    Accepts both on-disk shapes: the research convention nests the header
    under a ``"__meta__"`` key; this platform's writer uses the same form.
    """
    inner = line_obj.get("__meta__")
    if isinstance(inner, dict) and "n_records" in inner:
        return MetaHeader.model_validate(inner)
    keys = set(line_obj)
    if "n_records" in keys and ("builder" in keys or "built" in keys) and "task" not in keys:
        return MetaHeader.model_validate(line_obj)
    return None


def iter_jsonl(path: str | Path, *, strict: bool = True) -> Iterator[dict[str, Any]]:
    """Stream records from a gzip JSONL file.

    Args:
        path: corpus or archive file.
        strict: when ``True`` (default), corrupt lines raise; when ``False``
            they are skipped. A ``__meta__`` header line is yielded as-is
            first if present, so callers can distinguish it.
    """
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:  # pragma: no cover - I/O edge
                if strict:
                    raise GuardrailError(f"{path}:{lineno}: corrupt JSON line") from exc
                continue


def load_jsonl(
    path: str | Path, *, skip_meta: bool = True
) -> tuple[list[dict[str, Any]], MetaHeader | None]:
    """Load all records from a gzip JSONL file.

    Returns:
        ``(records, meta)`` where ``meta`` is the parsed ``__meta__`` header
        when present and ``skip_meta`` excluded it from ``records``.
    """
    records: list[dict[str, Any]] = []
    meta: MetaHeader | None = None
    for obj in iter_jsonl(path, strict=False):
        if meta is None and (m := parse_meta(obj)):
            meta = m
            if skip_meta:
                continue
        records.append(obj)
    return records, meta


def read_jsonl_resilient(path: str | Path) -> list[dict[str, Any]]:
    """Read every complete record, tolerating truncated/corrupt gzip files.

    Mirrors the recovery utility from the research scorer: on a broken gzip
    stream the raw bytes are re-streamed through raw zlib decompressors —
    one per gzip member, because append-mode writers concatenate members —
    and each complete JSON line is kept. Intended for evaluation archives
    written by processes that may have been killed mid-write.
    """
    try:
        records, _ = load_jsonl(path, skip_meta=False)
        return records
    except (EOFError, OSError, zlib.error, gzip.BadGzipFile):
        pass
    out: list[dict[str, Any]] = []
    raw = Path(path).read_bytes()
    text = _decompress_all_members(raw)
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # partial tail record from the killed writer
    return out


def _decompress_all_members(raw: bytes) -> str:
    """Decompress every concatenated gzip member, keeping partial tails."""
    chunks: list[str] = []
    data = raw
    while data:
        dec = zlib.decompressobj(16 + zlib.MAX_WBITS)
        try:
            chunks.append(dec.decompress(data).decode("utf-8", errors="replace"))
        except zlib.error:
            break
        data = dec.unused_data
        if not dec.eof and not data:
            break  # truncated final member; keep what we have
    return "".join(chunks)


def write_jsonl(
    path: str | Path,
    records: list[dict[str, Any]],
    *,
    meta: dict[str, Any] | None = None,
) -> int:
    """Write records (optionally preceded by a ``__meta__`` header) atomically-ish.

    The file is written to a sibling temp file and renamed, so readers never
    observe a partial corpus. Returns the number of data records written.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    n = 0
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        if meta is not None:
            # Research convention: header nested under "__meta__".
            f.write(json.dumps({"__meta__": meta}, ensure_ascii=False) + "\n")
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    tmp.rename(path)
    return n


def append_jsonl(path: str | Path, records: list[dict[str, Any]]) -> int:
    """Append records to a gzip JSONL file (archive resume protocol)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "at", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return len(records)


def archive_model_name(path: str | Path) -> tuple[str, str]:
    """Decode ``{model}__{dataset_tag}.jsonl.gz`` archive filenames.

    Model ids containing ``/`` are stored with ``/`` -> ``__`` per the
    research convention (e.g. ``nvidia__nemotron-3-super-120b-a12b:free__MB-20xx``).
    Only the FIRST ``__`` separates model from dataset tag; later ones belong
    to the flattened model id.
    """
    stem = Path(path).name.removesuffix(".jsonl.gz")
    model, _, tag = stem.partition("__")
    if not tag:
        raise GuardrailError(f"archive filename lacks __dataset tag: {path}")
    return model, tag
