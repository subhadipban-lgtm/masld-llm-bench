"""Feature extraction from prompt strings (baseline encoders).

The research baselines encode a prompt by regex-scraping ``KEY=value`` pairs
(the gene panel or geometric module activities) plus structured covariates
from the ``Patient:`` / ``Manifold:`` sentences. The same encoder serves raw
gene prompts and geometric ``M1..M9`` prompts by construction.
"""

from __future__ import annotations

import re
from typing import Any, Protocol

#: ``GENE123=1.23`` / ``M1=-0.65`` pairs, gene ids incl. dots/dashes.
_KEY_VALUE_RE = re.compile(r"([A-Za-z0-9_.\-]+)=(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)")

_MANIFOLD_POS_RE = re.compile(
    r"position\s*\((-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\)"
)
_MANIFOLD_DENSITY_RE = re.compile(r"\b(dense|moderate|sparse)\b", re.IGNORECASE)
_MANIFOLD_NEIGHBOUR_RE = re.compile(
    r"mean\s+neighbou?r\s+(?:fibrosis\s+)?stage\s+(-?\d+(?:\.\d+)?)", re.IGNORECASE
)
_DENSITY_ORDER = {"dense": 0.0, "moderate": 1.0, "sparse": 2.0}


def parse_features(prompt: str) -> dict[str, float]:
    """Extract all ``KEY=value`` numeric pairs from a prompt string."""
    out: dict[str, float] = {}
    for key, val in _KEY_VALUE_RE.findall(prompt):
        try:
            out[key] = float(val)
        except ValueError:  # pragma: no cover - regex guarantees parseable
            continue
    return out


def parse_clinical(prompt: str) -> dict[str, float]:
    """Extract covariates from the ``Patient:`` sentence.

    Returns any subset of ``{"age", "is_female", "t2dm"}``; missing fields are
    simply absent (the vectoriser zero-fills).
    """
    feats: dict[str, float] = {}
    m = re.search(r"Patient:\s*([^\n]+)", prompt)
    if not m:
        return feats
    line = m.group(1)
    age = re.search(r"\bage\s+(\d+(?:\.\d+)?)", line, re.IGNORECASE)
    if age:
        feats["age"] = float(age.group(1))
    # "no type-2 diabetes" must not match the t2dm keyword.
    if re.search(r"type-?2\s+diabetes", line, re.IGNORECASE) and not re.search(
        r"no\s+type-?2", line, re.IGNORECASE
    ):
        feats["t2dm"] = 1.0
    elif re.search(r"type-?2\s+diabetes", line, re.IGNORECASE):
        feats["t2dm"] = 0.0
    if re.search(r"\bfemale\b", line, re.IGNORECASE):
        feats["is_female"] = 1.0
    elif re.search(r"\bmale\b", line, re.IGNORECASE):
        feats["is_female"] = 0.0
    return feats


def parse_manifold(prompt: str) -> dict[str, float]:
    """Extract UMAP manifold features from geometric (MB-40xx) prompts.

    Fields: ``umap_x``, ``umap_y``, ``density_code`` (0=dense..2=sparse),
    ``neighbour_stage``.
    """
    feats: dict[str, float] = {}
    if (m := _MANIFOLD_POS_RE.search(prompt)) :
        feats["umap_x"] = float(m.group(1))
        feats["umap_y"] = float(m.group(2))
    if (m := _MANIFOLD_DENSITY_RE.search(prompt)) :
        feats["density_code"] = _DENSITY_ORDER[m.group(1).lower()]
    if (m := _MANIFOLD_NEIGHBOUR_RE.search(prompt)) :
        feats["neighbour_stage"] = float(m.group(1))
    return feats


class FeatureExtractor(Protocol):
    """One prompt -> feature-vector encoder (baseline input side).

    Domain encoders are registered by name; benchmarks pick them via the
    ``feature_mode`` string (a name, or ``+``-joined composite, or ``all``).
    """

    name: str

    def encode(self, prompt: str) -> dict[str, float]: ...


class KvPairsExtractor:
    """All ``KEY=value`` numeric pairs (gene panels, module activities, ...)."""

    name = "genes"

    def encode(self, prompt: str) -> dict[str, float]:
        return parse_features(prompt)


class ClinicalSentenceExtractor:
    """Covariates from the ``Patient:`` sentence (age / sex / t2dm)."""

    name = "clinical"

    def encode(self, prompt: str) -> dict[str, float]:
        return parse_clinical(prompt)


class ManifoldExtractor:
    """Module activities + UMAP manifold fields from geometric prompts."""

    name = "manifold"

    def encode(self, prompt: str) -> dict[str, float]:
        feats = parse_features(prompt)
        feats.update(parse_manifold(prompt))
        return feats


_EXTRACTORS: dict[str, FeatureExtractor] = {}


def register_extractor(ext: FeatureExtractor) -> FeatureExtractor:
    """Register (or replace) a feature extractor by its name."""
    _EXTRACTORS[ext.name] = ext
    return ext


def get_extractor(name: str) -> FeatureExtractor:
    if name not in _EXTRACTORS:
        raise ValueError(
            f"unknown feature extractor {name!r}; registered: {sorted(_EXTRACTORS)}"
        )
    return _EXTRACTORS[name]


for _ext in (KvPairsExtractor(), ClinicalSentenceExtractor(), ManifoldExtractor()):
    register_extractor(_ext)


def encode_prompt(prompt: str, *, mode: str = "genes") -> dict[str, float]:
    """Encode a prompt with a named extractor, a ``+`` composite, or ``all``.

    Modes: a single extractor name (``genes``), a composite (``genes+clinical``),
    or ``all`` (every registered extractor; later ones may overwrite keys).
    """
    if mode == "all":
        feats: dict[str, float] = {}
        for ext in _EXTRACTORS.values():
            feats.update(ext.encode(prompt))
        return feats
    feats = {}
    for name in mode.split("+"):
        feats.update(get_extractor(name.strip()).encode(prompt))
    return feats


def vectorise(rows: list[dict[str, Any]]) -> tuple[list[list[float]], list[str]]:
    """Union-of-keys feature matrix with zero-fill (train/test space mismatch).

    Returns:
        ``(matrix, columns)`` — matrix rows align 1:1 with ``rows``.
    """
    columns: list[str] = []
    seen: set[str] = set()
    for r in rows:
        for k in r:
            if k not in seen:
                seen.add(k)
                columns.append(k)
    index = {c: i for i, c in enumerate(columns)}
    mat = [[0.0] * len(columns) for _ in rows]
    for i, r in enumerate(rows):
        for k, v in r.items():
            mat[i][index[k]] = float(v)
    return mat, columns
