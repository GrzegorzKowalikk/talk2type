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
    from talk2type.overlay import OverlayWindow
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


def test_request_recording_sets_state(overlay, qt_app):
    overlay.request_recording("pl")
    qt_app.processEvents()

    assert overlay._state == "recording"
    assert overlay._lang == "PL"
    assert overlay._wave_timer.isActive()
    assert overlay._dot_timer.isActive()
    assert overlay.isVisible()


def test_request_recording_en_label(overlay, qt_app):
    overlay.request_recording("en")
    qt_app.processEvents()

    assert overlay._lang == "EN"
    assert overlay._state == "recording"


def test_request_processing_changes_state(overlay, qt_app):
    overlay.request_recording("pl")
    qt_app.processEvents()

    overlay.request_processing()
    qt_app.processEvents()

    assert overlay._state == "processing"
    assert not overlay._wave_timer.isActive()
    assert not overlay._dot_timer.isActive()


def test_request_hide_starts_fade_timer(overlay, qt_app):
    overlay.request_recording("pl")
    qt_app.processEvents()

    overlay.request_hide()
    qt_app.processEvents()

    assert overlay._fade_timer.isActive()
    assert not overlay._wave_timer.isActive()
    assert not overlay._dot_timer.isActive()


def test_fade_step_decrements_alpha(overlay, qt_app):
    overlay.request_recording("pl")
    qt_app.processEvents()

    assert overlay._alpha == 255
    overlay._fade_step()
    assert overlay._alpha == 235


def test_fade_step_hides_widget_at_zero(overlay, qt_app):
    overlay.request_recording("pl")
    qt_app.processEvents()

    overlay._alpha = 20
    overlay._fade_step()

    assert overlay._alpha == 0
    assert not overlay._fade_timer.isActive()
    qt_app.processEvents()
    assert not overlay.isVisible()


def test_toggle_dot_flips_state(overlay):
    initial = overlay._dot_on
    overlay._toggle_dot()
    assert overlay._dot_on is not initial
    overlay._toggle_dot()
    assert overlay._dot_on is initial


def test_recording_resets_alpha_to_255(overlay, qt_app):
    # Simulate partially faded state, then new recording resets alpha
    overlay.request_recording("pl")
    qt_app.processEvents()
    overlay._alpha = 100

    overlay.request_recording("en")
    qt_app.processEvents()

    assert overlay._alpha == 255
