"""Skills loader — loads bundled SKILL.md + metadata.json pairs into a backend.

Inspired by Hermes Agent's skills/ directory pattern.
Call `seed_bundled_skills(backend)` once at startup to pre-populate the memory
store with the curated starter skills shipped with LearnKit.

Usage:
    from learnkit.skills_loader import seed_bundled_skills
    lk = LearnKit()
    seed_bundled_skills(lk.backend)  # idempotent — skips already-present records
"""

import json
from pathlib import Path
from typing import Optional

from .backends.base import BaseBackend
from .logging import get_logger
from .schemas.skill import SkillRecord

logger = get_logger("skills_loader")

# Bundled skills are in the skills/ directory at the project root
_SKILLS_DIR = Path(__file__).parent.parent / "skills"


def seed_bundled_skills(
    backend: BaseBackend,
    skills_dir: Optional[Path] = None,
    overwrite: bool = False,
) -> int:
    """Load all bundled SKILL.md + metadata.json pairs into the backend.

    Parameters
    ----------
    backend:
        Any LearnKit backend (SQLite, Mem0, etc.)
    skills_dir:
        Path to the skills root directory. Defaults to the bundled ``skills/``
        directory shipped with LearnKit.
    overwrite:
        If False (default), records already present in the backend are skipped.
        If True, existing records are replaced.

    Returns
    -------
    int
        Number of skill records successfully seeded.
    """
    root = Path(skills_dir) if skills_dir else _SKILLS_DIR
    if not root.exists():
        logger.warning(
            "Skills directory not found, skipping seed",
            extra={"event": "skills_dir_missing", "path": str(root)},
        )
        return 0

    seeded = 0
    for metadata_path in sorted(root.rglob("metadata.json")):
        try:
            data = json.loads(metadata_path.read_text())

            skill_id = data.get("id")
            if not skill_id:
                logger.warning(
                    "Skill metadata missing 'id', skipping",
                    extra={"event": "skill_seed_no_id", "path": str(metadata_path)},
                )
                continue

            # Skip records already in backend (idempotent)
            if not overwrite and backend.read(skill_id) is not None:
                continue

            # Build SkillRecord from metadata.json
            # Fields not in MemoryRecord schema (e.g. version, outcome_quality) are dropped
            allowed_fields = SkillRecord.model_fields.keys()
            filtered = {k: v for k, v in data.items() if k in allowed_fields}
            record = SkillRecord(**filtered)

            # Attach SKILL.md text as human_readable content field if present
            skill_md_path = metadata_path.parent / "SKILL.md"
            if skill_md_path.exists():
                record.content["skill_md"] = skill_md_path.read_text()

            backend.add(record)
            seeded += 1
            logger.info(
                "Seeded skill",
                extra={
                    "event": "skill_seeded",
                    "skill_id": record.id,
                    "task_type": record.task_type,
                },
            )
        except Exception as e:
            logger.warning(
                "Failed to seed skill from metadata",
                extra={
                    "event": "skill_seed_fail",
                    "path": str(metadata_path),
                    "error_type": type(e).__name__,
                },
            )

    return seeded
