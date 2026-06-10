import pytest

from talk2type.core.states import DictationStateMachine, State


@pytest.fixture
def machine():
    return DictationStateMachine()


def _record_signals(machine):
    seen = []
    machine.recording_started.connect(lambda lang: seen.append(("rec", lang)))
    machine.processing_started.connect(lambda: seen.append(("proc",)))
    machine.returned_to_idle.connect(lambda reason: seen.append(("idle", reason)))
    return seen


def test_initial_state_is_idle(machine):
    assert machine.state is State.IDLE


def test_press_from_idle_starts_recording(machine):
    seen = _record_signals(machine)
    assert machine.press("pl") is True
    assert machine.state is State.RECORDING
    assert machine.lang == "pl"
    assert ("rec", "pl") in seen


def test_press_while_recording_rejected(machine):
    machine.press("pl")
    seen = _record_signals(machine)
    assert machine.press("en") is False
    assert machine.state is State.RECORDING
    assert seen == []


def test_release_moves_to_processing(machine):
    machine.press("pl")
    seen = _record_signals(machine)
    assert machine.release() is True
    assert machine.state is State.PROCESSING
    assert ("proc",) in seen


def test_release_from_idle_rejected(machine):
    assert machine.release() is False


def test_cancel_from_recording(machine):
    machine.press("pl")
    seen = _record_signals(machine)
    assert machine.cancel() is State.RECORDING
    assert machine.state is State.IDLE
    assert ("idle", "cancelled") in seen


def test_cancel_from_processing(machine):
    machine.press("pl")
    machine.release()
    assert machine.cancel() is State.PROCESSING
    assert machine.state is State.IDLE


def test_cancel_from_idle_is_noop(machine):
    seen = _record_signals(machine)
    assert machine.cancel() is None
    assert seen == []


def test_finish_from_processing(machine):
    machine.press("pl")
    machine.release()
    seen = _record_signals(machine)
    machine.finish("done")
    assert machine.state is State.IDLE
    assert ("idle", "done") in seen


def test_finish_only_acts_in_processing(machine):
    # guard: stale pipeline thread must not kill a new recording
    machine.press("pl")
    seen = _record_signals(machine)
    machine.finish("done")
    assert machine.state is State.RECORDING
    assert seen == []
