"""Hash-chained, append-only audit log.

Every event's ``hash`` covers its content and the previous event's hash, so
any retroactive modification breaks the chain and
:func:`verify_audit_chain` detects it. INSERT-only by convention; there is
no update or delete path anywhere in the platform.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from masld_persistence.models import AuditEvent

GENESIS = "0" * 64


def _ts_key(dt: datetime) -> str:
    """Canonical timestamp string for hashing.

    SQLite returns naive datetimes on read; this key uses only the stored
    field values, so it is identical at write time and after a round-trip.
    """
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")


def _event_hash(prev_hash: str, ts_key: str, actor: str, event: str, payload_json: str) -> str:
    material = f"{prev_hash}|{ts_key}|{actor}|{event}|{payload_json}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def append_audit(
    session: Session,
    *,
    event: str,
    actor: str = "system",
    payload: dict[str, Any] | None = None,
) -> AuditEvent:
    """Append one audit event; commits and returns the row."""
    from masld_persistence.models import utcnow

    payload = payload or {}
    prev = session.execute(
        select(AuditEvent).order_by(AuditEvent.id.desc()).limit(1)
    ).scalar_one_or_none()
    prev_hash = prev.hash if prev else GENESIS
    ts = utcnow()
    evt = AuditEvent(
        ts=ts,
        actor=actor,
        event=event,
        payload=payload,
        prev_hash=prev_hash,
        hash=_event_hash(
            prev_hash, _ts_key(ts), actor, event, json.dumps(payload, sort_keys=True)
        ),
    )
    session.add(evt)
    session.commit()
    return evt


def verify_audit_chain(session: Session) -> bool:
    """Recompute the chain; ``True`` only if every link verifies."""
    prev_hash = GENESIS
    for evt in session.execute(select(AuditEvent).order_by(AuditEvent.id)).scalars():
        expected = _event_hash(
            prev_hash,
            _ts_key(evt.ts),
            evt.actor,
            evt.event,
            json.dumps(evt.payload, sort_keys=True),
        )
        if evt.prev_hash != prev_hash or evt.hash != expected:
            return False
        prev_hash = evt.hash
    return True
