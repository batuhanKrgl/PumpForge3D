"""Tests for AppState signal emissions."""

import math

from PySide6.QtCore import QCoreApplication

from apps.PumpForge3D.app.state.app_state import AppState, make_default_inducer


def _ensure_app():
    if QCoreApplication.instance() is None:
        QCoreApplication([])


def test_app_state_emits_signals():
    _ensure_app()
    state = AppState(make_default_inducer())

    inducer_events = []
    triangle_events = []

    state.inducer_changed.connect(lambda inducer: inducer_events.append(inducer))
    state.triangles_changed.connect(lambda payload: triangle_events.append(payload))

    state.update_inducer_fields(slip_out=math.radians(7.0))

    assert len(inducer_events) == 1
    assert len(triangle_events) == 1
    payload = triangle_events[0]
    assert "inlet_hub" in payload
    assert "outlet_tip" in payload
