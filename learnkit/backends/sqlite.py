"""Task 1.4 — SQLite backend with FTS5.

Default backend. Zero dependencies, offline-capable.
Uses SQLite FTS5 for BM25 text search (inspired by Hermes session_search).
"""

import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from ..errors import BackendError
from ..logging import get_logger
from ..schemas.base import MemoryRecord, MemoryType
from ..schemas.fact import FactRecord
from ..schemas.failure import FailureRecord
from ..schemas.heuristic import HeuristicRecord
from ..schemas.preference import PreferenceRecord
from ..schemas.skill import SkillRecord
from ..schemas.strategy import StrategyRecord
from ..schemas.trace import TraceRecord
from .base import BaseBackend

logger = get_logger("sqlite_backend")

# Mirrors MemoryScope = Literal["user", "team", "public"] in schemas/base.py.
# Pydantic validates on construction, but `validate_assignment` defaults to
# False so `record.scope = "..."` after creation bypasses validation. This
# set is the defense-in-depth check at write time.
VALID_SCOPES: frozenset[str] = frozenset(("user", "team", "public"))

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
    data = json.loads(data_json)
    rec_type = data.get("type")
    cls = RECORD_TYPES.get(rec_type, MemoryRecord)
    return cls.model_validate_json(data_json)


def escape_fts(query: str) -> str:
    """Escape an arbitrary user query into a valid FTS5 MATCH expression.

    Two pitfalls this avoids:
      1. FTS5 reserved operators (AND, OR, NOT, NEAR) in the query — if a token
         like "and" lands unquoted in a `foo OR and OR bar` expression, FTS5
         raises a syntax error and the whole search falls back to empty.
      2. Punctuation like `-` (NOT prefix), `:` (column qualifier), `"`, `(`, `)`,
         `*` — same hazard.

    Strategy: strip everything but alnum/underscore/whitespace, then double-quote
    each surviving token so reserved words become literal phrases.
    """
    if not query:
        return ""
    safe = "".join(
        c if (c.isalnum() or c.isspace() or c == "_") else " " for c in query
    )
    words = [w for w in safe.split() if w]
    if not words:
        return ""
    quoted = [f'"{w}"' for w in words]
    if len(quoted) == 1:
        return quoted[0]
    return " OR ".join(quoted)


class SQLiteBackend(BaseBackend):
    """
    SQLite memory backend. Uses SQLite FTS5 for BM25 full-text search.
    """

    def __init__(self, db_path: str = "~/.learnkit/memory.db", embedder=None):
        self._is_memory = db_path == ":memory:"
        self._memory_conn: Optional[sqlite3.Connection] = None
        self.db_path = db_path if self._is_memory else Path(db_path).expanduser()
        if not self._is_memory:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.embedder = embedder

        self._vec_enabled = False
        self._vec_initialized = False
        self._vec_warned = False
        self._lock = threading.Lock()

        try:
            import sqlite_vec

            self._sqlite_vec = sqlite_vec
            self._vec_available = True
        except ImportError:
            self._sqlite_vec = None
            self._vec_available = False

        self._init_db()

    def _init_db(self) -> None:
        conn = self._conn()
        try:
            if not self._is_memory:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")

            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                """
                )
                conn.execute(
                    "INSERT OR IGNORE INTO metadata (key, value) VALUES ('schema_version', '1')"
                )

                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS records (
                        id TEXT PRIMARY KEY,
                        type TEXT NOT NULL,
                        domains TEXT,
                        task_type TEXT,
                        content TEXT,
                        confidence REAL DEFAULT 0.5,
                        reuse_count INTEGER DEFAULT 0,
                        success_rate REAL,
                        scope TEXT DEFAULT 'team',
                        status TEXT DEFAULT 'active',
                        created_at TEXT,
                        expires_at TEXT,
                        last_reinforced TEXT,
                        full_record TEXT
                    )
                """
                )

                try:
                    conn.execute(
                        """
                        CREATE VIRTUAL TABLE IF NOT EXISTS records_fts USING fts5(
                            id, task_type, content_text, domains_text
                        )
                    """
                    )
                except sqlite3.OperationalError:
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS records_fts (
                            id TEXT PRIMARY KEY, task_type TEXT, content_text TEXT, domains_text TEXT
                        )
                    """
                    )
        except sqlite3.Error as e:
            logger.error(
                "Database initialization failed", extra={"error_type": type(e).__name__}
            )
            raise BackendError(f"Database init failed: {e}") from e
        finally:
            self._close(conn)

    def _conn(self) -> sqlite3.Connection:
        if self._is_memory:
            if self._memory_conn is None:
                self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
                self._memory_conn.row_factory = sqlite3.Row
                if self._vec_available:
                    self._memory_conn.enable_load_extension(True)
                    self._sqlite_vec.load(self._memory_conn)
            return self._memory_conn

        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        if self._vec_available:
            conn.enable_load_extension(True)
            self._sqlite_vec.load(conn)
        return conn

    def _close(self, conn: sqlite3.Connection) -> None:
        if not self._is_memory:
            conn.close()

    def _ensure_vec_table(self, conn: sqlite3.Connection, dim: int):
        if not self._vec_initialized:
            with self._lock:
                if not self._vec_initialized:
                    try:
                        with conn:
                            conn.execute(
                                """
                                CREATE TABLE IF NOT EXISTS vec_mapping (
                                    id TEXT PRIMARY KEY
                                )
                            """
                            )
                            conn.execute(
                                f"""
                                CREATE VIRTUAL TABLE IF NOT EXISTS records_vec USING vec0(
                                    rowid INTEGER PRIMARY KEY,
                                    embedding float[{dim}]
                                )
                            """
                            )
                        self._vec_enabled = True
                    except sqlite3.Error as e:
                        logger.warning(
                            "Failed to initialize sqlite-vec table",
                            extra={"error_type": type(e).__name__},
                        )
                        self._vec_enabled = False
                    self._vec_initialized = True

    def _get_record_text(self, record: MemoryRecord) -> str:
        parts = [record.task_type or "", " ".join(record.domains.keys())]
        for value in record.content.values():
            if isinstance(value, list):
                parts.append(" ".join(str(item) for item in value))
            elif isinstance(value, dict):
                parts.append(" ".join(str(item) for item in value.values()))
            else:
                parts.append(str(value))
        return " ".join(parts)

    def add(self, record: MemoryRecord) -> str:
        # Validate scope at write time so an invalid value can't be persisted.
        # Without this, parse_record at read time would explode on a poisoned
        # row, with the original write site long gone from the stack.
        if record.scope not in VALID_SCOPES:
            raise BackendError(
                f"Invalid scope {record.scope!r} on record {record.id} "
                f"(type={record.type}); must be one of {sorted(VALID_SCOPES)}."
            )

        conn = self._conn()
        domains_text = " ".join(record.domains.keys())
        content_text = self._get_record_text(record)

        embedding = None
        if self.embedder:
            if self._vec_available:
                try:
                    embedding = self.embedder(content_text)
                    self._ensure_vec_table(conn, len(embedding))
                except Exception as e:
                    logger.warning(
                        "Embedding generation failed",
                        extra={"event": "embed_fail", "error_type": type(e).__name__},
                    )
            elif not self._vec_warned:
                logger.warning(
                    "Embedder provided but sqlite-vec is not installed. Falling back to BM25."
                )
                self._vec_warned = True

        try:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO records
                    (id, type, domains, task_type, content, confidence, reuse_count,
                     success_rate, scope, status, created_at, expires_at, full_record)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                    (
                        record.id,
                        record.type,
                        json.dumps(record.domains),
                        record.task_type,
                        json.dumps(record.content),
                        record.confidence,
                        record.reuse_count,
                        record.success_rate,
                        record.scope,
                        record.status,
                        record.created_at,
                        record.expires_at,
                        record.model_dump_json(),
                    ),
                )

                conn.execute("DELETE FROM records_fts WHERE id=?", (record.id,))
                conn.execute(
                    """
                    INSERT INTO records_fts (id, task_type, content_text, domains_text)
                    VALUES (?,?,?,?)
                """,
                    (record.id, record.task_type or "", content_text, domains_text),
                )

                if self._vec_enabled and embedding is not None:
                    # Manually handle rowid mapping
                    conn.execute(
                        "INSERT OR IGNORE INTO vec_mapping (id) VALUES (?)",
                        (record.id,),
                    )
                    cursor = conn.execute(
                        "SELECT rowid FROM vec_mapping WHERE id=?", (record.id,)
                    )
                    rowid = cursor.fetchone()[0]
                    import struct

                    embed_bytes = struct.pack(f"{len(embedding)}f", *embedding)
                    conn.execute("DELETE FROM records_vec WHERE rowid=?", (rowid,))
                    conn.execute(
                        "INSERT INTO records_vec (rowid, embedding) VALUES (?, ?)",
                        (rowid, embed_bytes),
                    )

        except sqlite3.Error as e:
            logger.error(
                "Failed to add record",
                extra={"event": "db_write_fail", "error_type": type(e).__name__},
            )
            raise BackendError(f"Add failed: {e}") from e
        finally:
            self._close(conn)

        return record.id

    def replace(self, record: MemoryRecord) -> str:
        return self.add(record)

    def read(self, id: str) -> Optional[MemoryRecord]:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT full_record FROM records WHERE id=?", (id,)
            ).fetchone()
            if row is None:
                return None
            return parse_record(row["full_record"])
        except sqlite3.Error as e:
            logger.warning(
                "Read failed",
                extra={"event": "db_read_fail", "error_type": type(e).__name__},
            )
            raise BackendError(f"Read failed: {e}") from e
        finally:
            self._close(conn)

    def remove(self, id: str) -> None:
        conn = self._conn()
        try:
            with conn:
                conn.execute("DELETE FROM records WHERE id=?", (id,))
                conn.execute("DELETE FROM records_fts WHERE id=?", (id,))
                if self._vec_enabled:
                    cursor = conn.execute(
                        "SELECT rowid FROM vec_mapping WHERE id=?", (id,)
                    )
                    row = cursor.fetchone()
                    if row:
                        conn.execute("DELETE FROM records_vec WHERE rowid=?", (row[0],))
                        conn.execute("DELETE FROM vec_mapping WHERE id=?", (id,))
        except sqlite3.Error as e:
            logger.error(
                "Remove failed",
                extra={"event": "db_remove_fail", "error_type": type(e).__name__},
            )
            raise BackendError(f"Remove failed: {e}") from e
        finally:
            self._close(conn)

    def search(
        self,
        query: str,
        record_type: Optional[MemoryType] = None,
        domain: Optional[str] = None,
        scope: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 8,
        exclude_stale: bool = True,
    ) -> list[MemoryRecord]:
        conn = self._conn()
        results = []
        try:
            cursor = conn.execute(
                "SELECT sql FROM sqlite_master WHERE name='records_fts'"
            )
            sql_def = cursor.fetchone()
            is_fts5 = sql_def and "using fts5" in sql_def["sql"].lower()

            fts_query = escape_fts(query)

            if is_fts5 and fts_query:
                sql = """
                    SELECT r.full_record, r.confidence, r.created_at,
                           -bm25(records_fts) as bm25_score
                    FROM records_fts
                    JOIN records r ON records_fts.id = r.id
                    WHERE records_fts MATCH ?
                      AND r.confidence >= ?
                      AND r.status != 'quarantine'
                """
                params = [fts_query, min_confidence]
            else:
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

            if is_fts5 and fts_query:
                sql += " ORDER BY (bm25_score * r.confidence) DESC LIMIT ?"
            else:
                sql += " ORDER BY r.confidence DESC LIMIT ?"

            params.append(limit)
            rows = conn.execute(sql, params).fetchall()

            for row in rows:
                try:
                    rec = parse_record(row["full_record"])
                    rec._bm25_score = (
                        row["bm25_score"] if (is_fts5 and fts_query) else 1.0
                    )
                    if not rec.is_expired():
                        results.append(rec)
                except Exception:
                    pass

        except sqlite3.OperationalError as e:
            logger.warning(
                "Search query failed, falling back to empty",
                extra={"event": "db_search_fail", "error_type": type(e).__name__},
            )
        finally:
            self._close(conn)

        return results

    def hybrid_search(
        self,
        query: str,
        record_type: Optional[MemoryType] = None,
        domain: Optional[str] = None,
        scope: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 8,
        exclude_stale: bool = True,
        alpha: float = 0.5,
    ) -> list[MemoryRecord]:
        if not self._vec_enabled or not self.embedder:
            return self.search(
                query, record_type, domain, scope, min_confidence, limit, exclude_stale
            )

        conn = self._conn()
        results = []
        try:
            query_embedding = self.embedder(query)
            import struct

            embed_bytes = struct.pack(f"{len(query_embedding)}f", *query_embedding)

            fts_query = escape_fts(query)

            # Check if FTS5 is available
            cursor = conn.execute(
                "SELECT sql FROM sqlite_master WHERE name='records_fts'"
            )
            sql_def = cursor.fetchone()
            is_fts5 = sql_def and "using fts5" in sql_def["sql"].lower()

            if is_fts5 and fts_query:
                sql = """
                    SELECT r.full_record, r.confidence,
                           COALESCE(f.bm25_score, 0.0) as bm25_score,
                           CASE WHEN v.embedding IS NOT NULL THEN vec_distance_cosine(v.embedding, ?) ELSE NULL END as dense_dist
                    FROM records r
                    LEFT JOIN (
                        SELECT id, -bm25(records_fts) as bm25_score
                        FROM records_fts
                        WHERE records_fts MATCH ?
                    ) f ON r.id = f.id
                    LEFT JOIN vec_mapping m ON r.id = m.id
                    LEFT JOIN records_vec v ON m.rowid = v.rowid
                    WHERE r.confidence >= ?
                      AND r.status != 'quarantine'
                """
                params = [embed_bytes, fts_query, min_confidence]
            else:
                sql = """
                    SELECT r.full_record, r.confidence,
                           0.0 as bm25_score,
                           CASE WHEN v.embedding IS NOT NULL THEN vec_distance_cosine(v.embedding, ?) ELSE NULL END as dense_dist
                    FROM records r
                    LEFT JOIN vec_mapping m ON r.id = m.id
                    LEFT JOIN records_vec v ON m.rowid = v.rowid
                    WHERE r.confidence >= ?
                      AND r.status != 'quarantine'
                """
                params = [embed_bytes, min_confidence]

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

            rows = conn.execute(sql, params).fetchall()

            scored = []
            for row in rows:
                try:
                    rec = parse_record(row["full_record"])
                    if rec.is_expired():
                        continue

                    bm25_score = row["bm25_score"] or 0.0
                    rec._bm25_score = bm25_score
                    dense_dist = (
                        row["dense_dist"] if row["dense_dist"] is not None else 2.0
                    )
                    dense_sim = 1.0 - (dense_dist / 2.0)

                    final_score = (alpha * dense_sim) + ((1 - alpha) * bm25_score)
                    scored.append((final_score, rec.confidence, rec))
                except Exception:
                    pass

            scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
            results = [rec for _, _, rec in scored[:limit]]

        except sqlite3.Error as e:
            logger.warning(
                "Hybrid search failed, falling back to BM25",
                extra={"event": "hybrid_fail", "error_type": type(e).__name__},
            )
            self._close(conn)
            return self.search(
                query, record_type, domain, scope, min_confidence, limit, exclude_stale
            )

        self._close(conn)
        return results

    def list_by_domain(self, domain: str, limit: int = 20) -> list[MemoryRecord]:
        conn = self._conn()
        try:
            rows = conn.execute(
                """
                SELECT full_record FROM records
                WHERE domains LIKE ? AND status = 'active'
                ORDER BY confidence DESC LIMIT ?
            """,
                (f'%"{domain}"%', limit),
            ).fetchall()
            return [parse_record(r["full_record"]) for r in rows]
        finally:
            self._close(conn)

    def list_by_scope(self, scope: str = "team", limit: int = 20) -> list[MemoryRecord]:
        conn = self._conn()
        try:
            rows = conn.execute(
                """
                SELECT full_record FROM records
                WHERE scope = ? AND status = 'active'
                ORDER BY confidence DESC LIMIT ?
            """,
                (scope, limit),
            ).fetchall()
            return [parse_record(r["full_record"]) for r in rows]
        finally:
            self._close(conn)

    def list_all(self, limit: int | None = None) -> list[MemoryRecord]:
        conn = self._conn()
        try:
            sql = "SELECT full_record FROM records ORDER BY created_at ASC"
            params = []
            if limit is not None:
                sql += " LIMIT ?"
                params.append(limit)
            rows = conn.execute(sql, params).fetchall()
            return [parse_record(r["full_record"]) for r in rows]
        finally:
            self._close(conn)

    def update_confidence(self, id: str, new_confidence: float) -> None:
        record = self.read(id)
        if record is None:
            return
        record.confidence = new_confidence
        self.add(record)

    def decay_confidence(self, weeks: int = 1, decay_rate: float = 0.02) -> int:
        conn = self._conn()
        try:
            rows = conn.execute(
                """
                SELECT full_record FROM records
                WHERE status IN ('active', 'stale')
            """
            ).fetchall()
        finally:
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
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
            hours=min_age_hours
        )
        promoted = 0

        for record in self._records_with_status("quarantine"):
            created_at = datetime.fromisoformat(record.created_at)
            if created_at <= cutoff:
                record.status = "active"
                self.add(record)
                promoted += 1
        return promoted

    def mark_expired_stale(self) -> int:
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
            record = RECORD_TYPES.get(item.get("type"), MemoryRecord).model_validate(
                item
            )
            self.add(record)
            imported += 1
        return imported

    def _records_with_status(self, status: str) -> list[MemoryRecord]:
        conn = self._conn()
        try:
            rows = conn.execute(
                """
                SELECT full_record FROM records
                WHERE status = ?
            """,
                (status,),
            ).fetchall()
            return [parse_record(r["full_record"]) for r in rows]
        finally:
            self._close(conn)
