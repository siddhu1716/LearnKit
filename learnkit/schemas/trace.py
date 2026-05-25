"""TraceRecord — full or compressed raw execution traces for retrieval-based recall."""

from .base import MemoryRecord


class TraceRecord(MemoryRecord):
    type: str = "trace"

    # Expected content keys:
    #   trajectory_id: str  — ID of the original Trajectory
    #   task: str           — the user's task
    #   summary: str        — summarized sequence of actions
    #   steps: list[dict]   — key steps from the trajectory
