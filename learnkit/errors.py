class LearnKitError(Exception):
    """Base class for all LearnKit exceptions."""

    pass


class ConfigurationError(LearnKitError):
    """Raised when a module is misconfigured (e.g. missing dependencies, invalid backend params)."""

    pass


class BackendError(LearnKitError):
    """Raised when a memory backend fails (e.g. connection error, missing table)."""

    pass


class RetrievalError(LearnKitError):
    """Raised when semantic retrieval or routing fails."""

    pass


class ClassificationError(LearnKitError):
    """Raised when task classification fails completely (unrecoverable)."""

    pass


class EvaluationError(LearnKitError):
    """Raised when quality evaluation fails unrecoverably."""

    pass


class DistillationError(LearnKitError):
    """Raised when trace distillation fails."""

    pass


class PostProcessError(LearnKitError):
    """Raised when the background post-processing loop encounters an error."""

    pass
