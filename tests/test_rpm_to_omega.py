import math

from apps.PumpForge3D.app.state.app_state import rpm_to_omega


def test_rpm_to_omega_conversion():
    omega = rpm_to_omega(6000.0)
    assert math.isclose(omega, 2.0 * math.pi * 100.0, rel_tol=1e-6)
