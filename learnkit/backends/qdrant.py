"""Qdrant backend adapter entry point.

The optional Qdrant dependency is not required for the default SQLite path.
"""


class QdrantBackend:
    def __init__(self, *args, **kwargs):
        raise ImportError(
            "QdrantBackend requires the optional 'qdrant' dependency. "
            "Install LearnKit with: pip install 'learnkit[qdrant]'"
        )
