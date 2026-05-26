import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from learnkit.backends.base import BaseBackend
from learnkit.schemas.base import MemoryRecord, MemoryType
from learnkit.schemas.fact import FactRecord
from learnkit.schemas.skill import SkillRecord


class DictBackend(BaseBackend):
    """A simple in-memory dict backend for testing the backend contract."""

    def __init__(self):
        self.records: dict[str, MemoryRecord] = {}

    def add(self, record: MemoryRecord) -> str:
        self.records[record.id] = record
        return record.id

    def read(self, id: str) -> Optional[MemoryRecord]:
        return self.records.get(id)

    def remove(self, id: str) -> None:
        self.records.pop(id, None)

    def search(
        self,
        query: str,
        record_type: Optional[MemoryType] = None,
        domain: Optional[str] = None,
        scope: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 8,
        exclude_stale: bool = True,
    ) -> List[MemoryRecord]:
        results = []
        for r in self.records.values():
            if record_type and r.type != record_type:
                continue
            if domain and domain not in r.domains:
                continue
            if scope and r.scope != scope:
                continue
            if r.confidence < min_confidence:
                continue
            if r.status == "quarantine":
                continue
            if exclude_stale and r.status == "stale":
                continue
            if r.is_expired():
                continue

            # Simple substring matching for dict search
            content_str = str(r.content) + (r.task_type or "")
            if query.lower() in content_str.lower():
                results.append(r)

        # Sort by confidence descending
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results[:limit]

    def list_by_domain(self, domain: str, limit: int = 20) -> List[MemoryRecord]:
        results = [
            r
            for r in self.records.values()
            if domain in r.domains and r.status == "active"
        ]
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results[:limit]

    def list_by_scope(self, scope: str = "team", limit: int = 20) -> List[MemoryRecord]:
        results = [
            r
            for r in self.records.values()
            if r.scope == scope and r.status == "active"
        ]
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results[:limit]

    def list_all(self, limit: Optional[int] = None) -> List[MemoryRecord]:
        results = list(self.records.values())
        results.sort(key=lambda x: x.created_at)
        if limit is not None:
            return results[:limit]
        return results

    def update_confidence(self, id: str, new_confidence: float) -> None:
        if id in self.records:
            self.records[id].confidence = new_confidence

    def decay_confidence(self, weeks: int = 1, decay_rate: float = 0.02) -> int:
        decayed = 0
        for r in self.records.values():
            if r.status in ("active", "stale"):
                for _ in range(weeks):
                    r.decay(decay_rate)
                decayed += 1
        return decayed

    def promote_quarantined(self, min_age_hours: float = 24.0) -> int:
        cutoff = datetime.utcnow() - timedelta(hours=min_age_hours)
        promoted = 0
        for r in self.records.values():
            if r.status == "quarantine":
                created = datetime.fromisoformat(r.created_at)
                if created <= cutoff:
                    r.status = "active"
                    promoted += 1
        return promoted

    def mark_expired_stale(self) -> int:
        marked = 0
        for r in self.records.values():
            if r.status == "active" and r.is_expired():
                r.status = "stale"
                marked += 1
        return marked

    def export_json(self, path: str | Path) -> int:
        payload = [r.model_dump(mode="json") for r in self.records.values()]
        Path(path).write_text(json.dumps(payload, indent=2) + "\n")
        return len(self.records)

    def import_json(self, path: str | Path) -> int:
        data = json.loads(Path(path).read_text())
        imported = 0
        for item in data:
            # Reconstruct record
            rec_type = item.get("type", "skill")
            if rec_type == "skill":
                rec = SkillRecord.model_validate(item)
            elif rec_type == "fact":
                rec = FactRecord.model_validate(item)
            else:
                rec = MemoryRecord.model_validate(item)
            self.add(rec)
            imported += 1
        return imported


def run_backend_contract_suite(backend: BaseBackend, tmp_path: Path):
    """Run all standard backend contract tests on a given backend instance."""
    # 1. Add and read record
    skill = SkillRecord(
        domains={"legal": 0.9},
        task_type="nda_review",
        content={"steps": ["check governing law"], "tools_used": ["pdf"]},
        confidence=0.85,
    )
    backend.add(skill)

    retrieved = backend.read(skill.id)
    assert retrieved is not None
    assert isinstance(retrieved, SkillRecord)
    assert retrieved.task_type == "nda_review"
    assert retrieved.confidence == 0.85

    # 2. Search filtering
    results = backend.search("NDA", domain="legal")
    assert len(results) == 1
    assert results[0].id == skill.id

    # Filter out by min_confidence
    assert len(backend.search("NDA", min_confidence=0.9)) == 0

    # 3. Expiration & Stale Lifecycle
    expired = FactRecord(
        domains={"legal": 0.8},
        content={"statement": "Old document"},
        expires_at=(datetime.utcnow() - timedelta(days=1)).isoformat(),
    )
    backend.add(expired)

    # expired record excluded from standard search
    assert len(backend.search("document")) == 0

    # stale marking works
    stale_count = backend.mark_expired_stale()
    assert stale_count >= 1
    assert backend.read(expired.id).status == "stale"

    # 4. Quarantine promotion
    quarantined = SkillRecord(
        domains={"legal": 0.9},
        task_type="draft_skill",
        content={"steps": ["draft"]},
        status="quarantine",
        created_at=(datetime.utcnow() - timedelta(hours=25)).isoformat(),
    )
    backend.add(quarantined)

    # quarantined is not returned in search
    assert len(backend.search("draft")) == 0

    # promotion works
    promoted = backend.promote_quarantined(min_age_hours=24)
    assert promoted >= 1
    assert backend.read(quarantined.id).status == "active"
    assert len(backend.search("draft")) == 1

    # 5. List domain & scope
    assert len(backend.list_by_domain("legal")) >= 1
    assert len(backend.list_by_scope("team")) >= 1

    # 6. JSON export/import
    export_file = tmp_path / "export_contract.json"
    exported_count = backend.export_json(export_file)
    assert exported_count >= 2

    # Import into a fresh backend (we can use DictBackend for safety or a fresh sqlite)
    fresh_backend = DictBackend()
    imported_count = fresh_backend.import_json(export_file)
    assert imported_count == exported_count
    assert fresh_backend.read(skill.id) is not None
    assert fresh_backend.read(skill.id).task_type == "nda_review"

    # 7. update & decay confidence
    backend.update_confidence(skill.id, 0.5)
    assert backend.read(skill.id).confidence == 0.5

    decayed_count = backend.decay_confidence(weeks=2, decay_rate=0.05)
    assert decayed_count >= 1
    # skill confidence was 0.5, decayed 5% twice: 0.5 - 2*0.025 (actually skill confidence decay is 0.5 * 0.95 * 0.95 = 0.45125 or simple 0.5 - 2*0.05*0.5)
    # let's assert confidence is less than 0.5
    assert backend.read(skill.id).confidence < 0.5

    # 8. CRUD deletion
    backend.remove(skill.id)
    assert backend.read(skill.id) is None


def test_dict_backend_passes_contract(tmp_path):
    """Verify that DictBackend correctly satisfies the BaseBackend contract."""
    backend = DictBackend()
    run_backend_contract_suite(backend, tmp_path)
