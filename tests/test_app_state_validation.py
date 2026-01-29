from apps.PumpForge3D.app.state.app_state import AppState


def test_invalid_state_update_does_not_apply():
    state = AppState.create_default()
    original = state.get_inducer().r_in_hub

    state.update_inducer_fields(r_in_hub=-1.0)

    assert state.get_inducer().r_in_hub == original
