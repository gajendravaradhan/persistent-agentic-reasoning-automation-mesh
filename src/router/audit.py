"""Audit logger with JSONL persistence and SHA256-based de-duplication.

Tracks every routing decision for observability, drift detection, and compliance.
"""
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from .types import AuditEntry


class AuditLogger:
    """Persistent audit logger.

    Writes structured JSONL entries to ``audit_log.jsonl``, de-duplicates by
    SHA-256 request hash, and provides aggregate statistics via ``get_stats()``.
    """

    def __init__(self, log_path: Optional[str] = None) -> None:
        if log_path is None:
            log_path = str(Path(__file__).parent / "audit_log.jsonl")
        self.log_path = Path(log_path)
        self._seen_hashes: set[str] = set()
        self._load_seen_hashes()

    def _load_seen_hashes(self) -> None:
        """Pre-load existing request hashes from the log file.

        This ensures in-memory de-duplication matches what is already
        persisted, so restarting the process does not re-log old entries.
        """
        if not self.log_path.exists():
            return
        for line in self.log_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry: Dict[str, Any] = json.loads(line)
                self._seen_hashes.add(entry.get("request_hash", ""))
            except json.JSONDecodeError:
                continue

    def log(self, entry: AuditEntry) -> None:
        """Persist an audit entry.

        Silently skips entries whose ``request_hash`` has already been logged
        (SHA-256 de-duplication).

        Args:
            entry: An ``AuditEntry`` dataclass instance.
        """
        if entry.request_hash in self._seen_hashes:
            return
        self._seen_hashes.add(entry.request_hash)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "a") as f:
            f.write(json.dumps(asdict(entry), default=str) + "\n")

    def get_stats(self) -> Dict[str, Any]:
        """Compute aggregate routing statistics from the audit log.

        Returns:
            A dict with:
                - total_entries (int): number of logged entries
                - intent_distribution (dict): count per intent value
                - confidence_avg (float): mean confidence across all entries
                - route_distribution (dict): count per route name
                - guard_trigger_rate (float): fraction of entries where
                  outcome was "blocked" or "fallback"
        """
        entries: List[Dict[str, Any]] = []
        if self.log_path.exists():
            for line in self.log_path.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        total = len(entries)
        if total == 0:
            return {
                "total_entries": 0,
                "intent_distribution": {},
                "confidence_avg": 0.0,
                "route_distribution": {},
                "guard_trigger_rate": 0.0,
            }

        intent_dist: Dict[str, int] = {}
        route_dist: Dict[str, int] = {}
        guard_triggered: int = 0
        conf_sum: float = 0.0

        for e in entries:
            intent = e.get("intent", "unknown")
            route = e.get("route", "unknown")
            intent_dist[intent] = intent_dist.get(intent, 0) + 1
            route_dist[route] = route_dist.get(route, 0) + 1
            conf_sum += e.get("confidence", 0.0)
            if e.get("outcome") in ("blocked", "fallback"):
                guard_triggered += 1

        return {
            "total_entries": total,
            "intent_distribution": intent_dist,
            "confidence_avg": round(conf_sum / total, 4),
            "route_distribution": route_dist,
            "guard_trigger_rate": round(guard_triggered / total, 4),
        }
