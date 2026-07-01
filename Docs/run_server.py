"""Launcher for the dashboard FastAPI service.

Set LEARNKIT_DB_PATH before running to pin the SQLite store. Defaults to
~/.learnkit/memory.db so local development works out of the box.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault(
    "LEARNKIT_DB_PATH", str(Path.home() / ".learnkit" / "memory.db")
)
# The dashboard store is persist-until-deleted: records written while the
# server is up never expire, so they keep showing in the UI until explicitly
# removed. See learnkit.schemas.base._persist_forever.
os.environ.setdefault("LEARNKIT_PERSIST_FOREVER", "1")

import uvicorn  # noqa: E402

from Docs.server import app  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8090, log_level="warning")
