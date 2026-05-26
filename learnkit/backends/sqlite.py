"""Task 1.4 — SQLite backend with FTS5.

Default backend. Zero dependencies, offline-capable.
Uses SQLite FTS5 for BM25 text search (inspired by Hermes session_search).
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from .base import BaseBackend
from ..schemas.base import MemoryRecord, MemoryType
from ..schemas.skill import SkillRecord
from ..schemas.fact import FactRecord
from ..schemas.failure import FailureRecord
from ..schemas.strategy import StrategyRecord
from ..schemas.preference import PreferenceRecord
from ..schemas.trace import TraceRecord
from ..schemas.heuristic import HeuristicRecord

RECORD_TYPES = {
    "skill": SkillRecord,
    "fact": FactRecord,
    "failure": FailureRecord,
    "strategy": StrategyRecord,
    "preference": PreferenceRecord,
    "trace": TraceRecord,
    "heuristic": HeuristicRecord,
}


def parse_record(data_json: str) -> MemoryRecord:
    """Parse JSON string into the correct MemoryRecord subclass."""
    data = json.loads(data_json)
    rec_type = data.get("type")
    cls = RECORD_TYPES.get(rec_type, MemoryRecord)
    return cls.model_validate_json(data_json)


class SQLiteBackend(BaseBackend):
    """
    SQLite memory backend. Uses SQLite FTS5 for BM25 full-text search.
    """

    def __init__(self, db_path: str = "~/.learnkit/memory.db"):
        self._is_memory = db_path == ":memory:"
        self._memory_conn: Optional[sqlite3.Connection] = None
        self.db_path = db_path if self._is_memory else Path(db_path).expanduser()
        if not self._is_memory:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        conn = self._conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                domains TEXT,        -- JSON
                task_type TEXT,
                content TEXT,        -- JSON
                confidence REAL DEFAULT 0.5,
                reuse_count INTEGER DEFAULT 0,
                success_rate REAL,
                scope TEXT DEFAULT 'team',
                status TEXT DEFAULT 'active',
                created_at TEXT,
                expires_at TEXT,
                last_reinforced TEXT,
                full_record TEXT     -- full JSON for round-trip
            )
        """)
        # FTS5 virtual table for BM25 search.
        # We store the ID and flat searchable fields directly in FTS.
        try:
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS records_fts USING fts5(
                    id,
                    task_type,
                    content_text,        -- flattened text of content dict
                    domains_text         -- flattened domain names
                )
            """)
        except sqlite3.OperationalError:
            # Fallback if FTS5 is not available on some minimal Python builds
            conn.execute("""
                CREATE TABLE IF NOT EXISTS records_fts (
                    id TEXT PRIMARY KEY,
                    task_type TEXT,
                    content_text TEXT,
                    domains_text TEXT
                )
            """)
        conn.commit()
        self._close(conn)

    def _conn(self) -> sqlite3.Connection:
        if self._is_memory:
            if self._memory_conn is None:
                self._memory_conn = sqlite3.connect(":memory:")
                self._memory_conn.row_factory = sqlite3.Row
            return self._memory_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _close(self, conn: sqlite3.Connection) -> None:
        if not self._is_memory:
            conn.close()

    def add(self, record: MemoryRecord) -> str:
        conn = self._conn()
        domains_text = " ".join(record.domains.keys())
        
        # Flatten content dict values for text search indexing
        vals = []
        for v in record.content.values():
            if isinstance(v, list):
                vals.append(" ".join(str(item) for item in v))
            elif isinstance(v, dict):
                vals.append(" ".join(str(item) for item in v.values()))
            else:
                vals.append(str(v))
        content_text = " ".join(vals)

        conn.execute("""
            INSERT OR REPLACE INTO records 
            (id, type, domains, task_type, content, confidence, reuse_count,
             success_rate, scope, status, created_at, expires_at, full_record)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            record.id, record.type, json.dumps(record.domains),
            record.task_type, json.dumps(record.content),
            record.confidence, record.reuse_count, record.success_rate,
            record.scope, record.status, record.created_at, record.expires_at,
            record.model_dump_json()
        ))
        
        # Handle FTS5 or fallback table indexing
        conn.execute("DELETE FROM records_fts WHERE id=?", (record.id,))
        conn.execute("""
            INSERT INTO records_fts (id, task_type, content_text, domains_text)
            VALUES (?,?,?,?)
        """, (record.id, record.task_type or "", content_text, domains_text))
        
        conn.commit()
        self._close(conn)
        return record.id

    def replace(self, record: MemoryRecord) -> str:
        return self.add(record)

    def read(self, id: str) -> Optional[MemoryRecord]:
        conn = self._conn()
        row = conn.execute("SELECT full_record FROM records WHERE id=?", (id,)).fetchone()
        self._close(conn)
        if row is None:
            return None
        return parse_record(row["full_record"])

    def remove(self, id: str) -> None:
        conn = self._conn()
        conn.execute("DELETE FROM records WHERE id=?", (id,))
        conn.execute("DELETE FROM records_fts WHERE id=?", (id,))
        conn.commit()
        self._close(conn)

    def search(
        self,
        query: str,
        record_type: Optional[MemoryType] = None,
        domain: Optional[str] = None,
        scope: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 8,
        exclude_stale: bool = True
    ) -> list[MemoryRecord]:
        """
        BM25 full-text search. Returns records ranked by score * confidence.
        """
        conn = self._conn()
        
        # Check if records_fts is a virtual FTS5 table
        cursor = conn.execute("SELECT sql FROM sqlite_master WHERE name='records_fts'")
        sql_def = cursor.fetchone()
        is_fts5 = sql_def and "using fts5" in sql_def["sql"].lower()

        if is_fts5:
            # Split multi-word queries into OR-joined terms for cross-column matching.
            # Phrase matching ("word1 word2") requires adjacent words in the SAME column,
            # which fails when terms appear across task_type/content_text/domains_text.
            words = query.split()
            if len(words) > 1:
                fts_query = " OR ".join(words)
            else:
                fts_query = query
            
            sql = """
                SELECT r.full_record, r.confidence, r.created_at,
                       bm25(records_fts) as bm25_score
                FROM records_fts
                JOIN records r ON records_fts.id = r.id
                WHERE records_fts MATCH ?
                  AND r.confidence >= ?
                  AND r.status != 'quarantine'
            """
            params = [fts_query, min_confidence]
        else:
            # Fallback when FTS5 is not available (uses LIKE)
            sql = """
                SELECT r.full_record, r.confidence, r.created_at,
                       1.0 as bm25_score
                FROM records_fts f
                JOIN records r ON f.id = r.id
                WHERE (f.task_type LIKE ? OR f.content_text LIKE ? OR f.domains_text LIKE ?)
                  AND r.confidence >= ?
                  AND r.status != 'quarantine'
            """
            like_q = f"%{query}%"
            params = [like_q, like_q, like_q, min_confidence]

        if record_type:
            sql += " AND r.type = ?"
            params.append(record_type)
        if domain:
            sql += " AND r.domains LIKE ?"
            params.append(f'%"{domain}"%')
        if scope:
            sql += " AND r.scope = ?"
            params.append(scope)
        if exclude_stale:
            sql += " AND r.status != 'stale'"

        if is_fts5:
            sql += " ORDER BY (bm25_score * r.confidence) DESC LIMIT ?"
        else:
            sql += " ORDER BY r.confidence DESC LIMIT ?"
        
        params.append(limit)

        try:
            rows = conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            # If MATCH fails for whatever syntax reason, fallback to query without match
            rows = []
        self._close(conn)

        results = []
        for row in rows:
            try:
                rec = parse_record(row["full_record"])
                if not rec.is_expired():
                    results.append(rec)
            except Exception:
                pass
        return results

    def list_by_domain(self, domain: str, limit: int = 20) -> list[MemoryRecord]:
        conn = self._conn()
        rows = conn.execute("""
            SELECT full_record FROM records
            WHERE domains LIKE ? AND status = 'active'
            ORDER BY confidence DESC LIMIT ?
        """, (f'%"{domain}"%', limit)).fetchall()
        self._close(conn)
        return [parse_record(r["full_record"]) for r in rows]

    def list_by_scope(self, scope: str = "team", limit: int = 20) -> list[MemoryRecord]:
        conn = self._conn()
        rows = conn.execute("""
            SELECT full_record FROM records
            WHERE scope = ? AND status = 'active'
            ORDER BY confidence DESC LIMIT ?
        """, (scope, limit)).fetchall()
        self._close(conn)
        return [parse_record(r["full_record"]) for r in rows]

    def list_all(self, limit: int | None = None) -> list[MemoryRecord]:
        conn = self._conn()
        sql = "SELECT full_record FROM records ORDER BY created_at ASC"
        params = []
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        self._close(conn)
        return [parse_record(r["full_record"]) for r in rows]

    def update_confidence(self, id: str, new_confidence: float) -> None:
        record = self.read(id)
        if record is None:
            return
        record.confidence = new_confidence
        self.add(record)

    def decay_confidence(self, weeks: int = 1, decay_rate: float = 0.02) -> int:
        """Apply weekly confidence decay to active or stale records."""
        conn = self._conn()
        rows = conn.execute("""
            SELECT full_record FROM records
            WHERE status IN ('active', 'stale')
        """).fetchall()
        self._close(conn)

        decayed = 0
        for row in rows:
            record = parse_record(row["full_record"])
            for _ in range(weeks):
                record.decay(decay_rate)
            self.add(record)
            decayed += 1
        return decayed

    def promote_quarantined(self, min_age_hours: float = 24.0) -> int:
        """Promote quarantined records to active after the review window."""
        cutoff = datetime.utcnow() - timedelta(hours=min_age_hours)
        promoted = 0

        for record in self._records_with_status("quarantine"):
            created_at = datetime.fromisoformat(record.created_at)
            if created_at <= cutoff:
                record.status = "active"
                self.add(record)
                promoted += 1
        return promoted

    def mark_expired_stale(self) -> int:
        """Mark expired active records stale without deleting their audit trail."""
        marked = 0
        for record in self._records_with_status("active"):
            if record.is_expired():
                record.status = "stale"
                self.add(record)
                marked += 1
        return marked

    def export_json(self, path: str | Path) -> int:
        records = self.list_all()
        output_path = Path(path).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [record.model_dump(mode="json") for record in records]
        output_path.write_text(json.dumps(payload, indent=2) + "\n")
        return len(records)

    def import_json(self, path: str | Path) -> int:
        input_path = Path(path).expanduser()
        payload = json.loads(input_path.read_text())
        if not isinstance(payload, list):
            raise ValueError("LearnKit import expects a JSON list of memory records")

        imported = 0
        for item in payload:
            record = RECORD_TYPES.get(item.get("type"), MemoryRecord).model_validate(item)
            self.add(record)
            imported += 1
        return imported

    def _records_with_status(self, status: str) -> list[MemoryRecord]:
        conn = self._conn()
        rows = conn.execute("""
            SELECT full_record FROM records
            WHERE status = ?
        """, (status,)).fetchall()
        self._close(conn)
        return [parse_record(r["full_record"]) for r in rows]
