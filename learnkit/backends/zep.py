"""Zep backend adapter entry point.

The optional Zep dependency is not required for the default SQLite path.
"""


class ZepBackend:
    def __init__(self, *args, **kwargs):
        raise ImportError(
            "ZepBackend requires the optional 'zep' dependency. "
            "Install LearnKit with: pip install 'learnkit[zep]'"
        )
