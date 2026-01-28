import math

from core.inducer import Inducer
from apps.PumpForge3D.app.state.app_state import make_default_inducer


def test_spanwise_triangles_linear_distribution():
    inducer = make_default_inducer()
    span_count = 7
    beta_in = Inducer.linear_span_distribution(math.radians(20.0), math.radians(40.0), span_count)
    beta_out = Inducer.linear_span_distribution(math.radians(50.0), math.radians(70.0), span_count)

    inducer = inducer.set_beta_blade_distribution(beta_in, beta_out)
    triangles = inducer.build_spanwise_triangles()

    assert len(triangles) == span_count
    assert math.isclose(triangles[0][0].beta_blade, beta_in[0])
    assert math.isclose(triangles[span_count - 1][0].beta_blade, beta_in[-1])
    assert math.isclose(triangles[0][1].beta_blade, beta_out[0])
    assert math.isclose(triangles[span_count - 1][1].beta_blade, beta_out[-1])
