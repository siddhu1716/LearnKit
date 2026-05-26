"""Mem0 backend adapter entry point.

The optional Mem0 dependency is not required for the default SQLite path.
"""


class Mem0Backend:
    def __init__(self, *args, **kwargs):
        raise ImportError(
            "Mem0Backend requires the optional 'mem0' dependency. "
            "Install LearnKit with: pip install 'learnkit[mem0]'"
        )
