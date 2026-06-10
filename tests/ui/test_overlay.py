import sys
import pytest


@pytest.fixture(scope="session")
def qt_app():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def overlay(qt_app):
    from talk2type.ui.overlay import OverlayWindow
    w = OverlayWindow()
    yield w
    if w.isVisible():
        w.hide()


def test_push_rms_scale_and_clamp(overlay):
    overlay.push_rms(0.05)
    assert overlay._rms[-1] == pytest.approx(0.5)

    overlay.push_rms(0.15)  # 0.15 * 10 = 1.5 → clamp 1.0
    assert overlay._rms[-1] == pytest.approx(1.0)

    overlay.push_rms(0.0)
    assert overlay._rms[-1] == pytest.approx(0.0)


def test_on_recording_sets_state(overlay):
    overlay.on_recording("pl")

    assert overlay._state == "recording"
    assert overlay._lang == "PL"
    assert overlay._wave_timer.isActive()
    assert overlay._pulse_timer.isActive()
    assert overlay.isVisible()


def test_on_recording_en_label(overlay):
    overlay.on_recording("en")

    assert overlay._lang == "EN"
    assert overlay._state == "recording"


def test_on_processing_changes_state(overlay):
    overlay.on_recording("pl")
    overlay.on_processing()

    assert overlay._state == "processing"
    assert not overlay._wave_timer.isActive()


def test_on_idle_starts_fade_timer(overlay):
    overlay.on_recording("pl")
    overlay.on_idle("done")

    assert overlay._fade_timer.isActive()
    assert not overlay._wave_timer.isActive()
    assert not overlay._pulse_timer.isActive()


def test_fade_step_decrements_alpha(overlay):
    overlay.on_recording("pl")

    assert overlay._alpha == 255
    overlay._fade_step()
    assert overlay._alpha == 235


def test_fade_step_hides_widget_at_zero(overlay):
    overlay.on_recording("pl")

    overlay._alpha = 20
    overlay._fade_step()

    assert overlay._alpha == 0
    assert not overlay._fade_timer.isActive()
    assert not overlay.isVisible()


def test_recording_resets_alpha_to_255(overlay):
    # Simulate partially faded state, then new recording resets alpha
    overlay.on_recording("pl")
    overlay._alpha = 100

    overlay.on_recording("en")

    assert overlay._alpha == 255


def test_on_idle_hides_after_fade(overlay, qt_app):
    overlay.on_recording("pl")
    overlay.on_idle("cancelled")
    assert overlay._fade_timer.isActive()
    for _ in range(20):
        overlay._fade_step()
    assert not overlay.isVisible()


def test_pill_is_compact():
    from talk2type.ui import overlay as mod
    assert mod._W <= 300 and mod._H <= 56
