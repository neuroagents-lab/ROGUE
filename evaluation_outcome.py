"""Shared evaluation outcomes used by getters and runners."""


SKIPPED_RESULT_MARKER = "skipped"


class EvaluationSkipped(RuntimeError):
    """Raised when an evaluator cannot run because optional infrastructure is absent."""
