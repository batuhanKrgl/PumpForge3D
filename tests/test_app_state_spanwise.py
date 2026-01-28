import math

from apps.PumpForge3D.app.state.app_state import AppState


def test_beta_table_edit_updates_single_station():
    state = AppState.create_default()
    initial_triangles = state.get_spanwise_triangles()
    unchanged_beta = initial_triangles[1][0].beta_blade

    state.apply_beta_table_edit({"index": 2, "side": "inlet", "value_deg": 33.0})

    updated_triangles = state.get_spanwise_triangles()
    assert math.isclose(updated_triangles[2][0].beta_blade, math.radians(33.0))
    assert math.isclose(updated_triangles[1][0].beta_blade, unchanged_beta)


def test_linear_inlet_edit_updates_distribution():
    state = AppState.create_default()
    state.set_linear_modes(inlet=True, outlet=False)

    state.apply_beta_table_edit({"index": 0, "side": "inlet", "value_deg": 10.0})
    distribution = state.get_beta_distribution_deg()
    beta_in = distribution["beta_in_deg"]

    assert math.isclose(beta_in[0], 10.0)
    assert math.isclose(beta_in[-1], beta_in[-1])
    mid_index = len(beta_in) // 2
    expected_mid = beta_in[0] + (beta_in[-1] - beta_in[0]) * (mid_index / (len(beta_in) - 1))
    assert math.isclose(beta_in[mid_index], expected_mid)
