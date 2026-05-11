import pytest

from backend.src.api.models import SolverJobStatus
from backend.src.application.jobs import JobStateMachine


def test_allows_expected_transitions() -> None:
    sm = JobStateMachine()

    assert sm.transition(SolverJobStatus.QUEUED, SolverJobStatus.RUNNING) == SolverJobStatus.RUNNING
    assert sm.transition(SolverJobStatus.QUEUED, SolverJobStatus.CANCELLED) == SolverJobStatus.CANCELLED
    assert sm.transition(SolverJobStatus.RUNNING, SolverJobStatus.FINISHED) == SolverJobStatus.FINISHED
    assert sm.transition(SolverJobStatus.RUNNING, SolverJobStatus.FAILED) == SolverJobStatus.FAILED
    assert sm.transition(SolverJobStatus.RUNNING, SolverJobStatus.CANCELLED) == SolverJobStatus.CANCELLED


def test_rejects_invalid_transition() -> None:
    sm = JobStateMachine()

    with pytest.raises(ValueError):
        sm.transition(SolverJobStatus.QUEUED, SolverJobStatus.FINISHED)
    with pytest.raises(ValueError):
        sm.transition(SolverJobStatus.RUNNING, SolverJobStatus.QUEUED)


def test_terminal_states_cannot_transition() -> None:
    sm = JobStateMachine()

    for status in [
        SolverJobStatus.FINISHED,
        SolverJobStatus.FAILED,
        SolverJobStatus.CANCELLED,
    ]:
        with pytest.raises(ValueError):
            sm.transition(status, SolverJobStatus.RUNNING)