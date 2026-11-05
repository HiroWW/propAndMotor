import math

import numpy as np
import pytest

import propmotor as pm
from propmotor.selection import TestSpec as Spec
from propmotor.selection import evaluate, voltage_band


@pytest.fixture(scope="module")
def props():
    return pm.apc_8x3_8sf_measured(), pm.apc_8x3_8sf_design()


@pytest.fixture
def motor():
    return pm.Motor("2212-920 test", kv=920, r_ohm=0.12, i0_a=0.4, i_max_a=15)


def test_apc_parser_static_row():
    apc = pm.apc_8x3_8sf_theory()
    assert apc.rpm[0] == 1000 and apc.rpm[-1] == 29000
    i = int(np.where(apc.rpm == 8000)[0][0])
    assert apc.ct[i] == pytest.approx(0.1372)
    assert apc.cp[i] == pytest.approx(0.0544)
    # APC's own dimensional value at 8000 rpm (5.097 N, 54.766 W) uses its rho (~1.225)
    assert apc.thrust(8000, 1.225) == pytest.approx(5.097, rel=0.01)
    assert apc.power(8000, 1.225) == pytest.approx(54.766, rel=0.01)


def test_fm_matches_apc_column():
    apc = pm.apc_8x3_8sf_theory()
    fom = pm.propeller.load_apc_dat(pm.propeller._data_path("props", "apc", "PER3_8x38SF.dat")).blocks[8000]["FOM"][0]
    assert apc.figure_of_merit(8000) == pytest.approx(fom, abs=2e-3)


def test_fm_definition_is_momentum_theory(props):
    uiuc, _ = props
    rho, rpm = 1.2, 6000.0
    p_ideal = uiuc.ideal_power(uiuc.thrust(rpm, rho), rho)
    assert p_ideal / uiuc.power(rpm, rho) == pytest.approx(uiuc.figure_of_merit(rpm), rel=1e-9)


def test_measured_extrapolation_flagged(props):
    uiuc, _ = props
    assert not uiuc.is_extrapolated(5000)
    assert uiuc.is_extrapolated(8125)
    assert uiuc.ct_at(8125) > uiuc.ct_at(7015)


def test_energy_balance(props, motor):
    uiuc, _ = props
    dt = pm.Drivetrain(prop=uiuc, motor=motor, esc=pm.generic_esc(), source=pm.KIKUSUI_PWR401L.at(12.0), rho=1.2)
    op = pm.at_rpm(dt, np.array([3000.0, 6000.0, 8000.0]))
    lhs = op.p_source
    rhs = op.p_shaft + op.p_cu + op.p_noload + op.p_esc + op.p_lead
    np.testing.assert_allclose(lhs, rhs, rtol=1e-9)
    # ESC input current is d * I_m (+ quiescent): smaller than the motor current
    assert np.all(op.i_in < op.i_motor)


def test_duty_rpm_inverse(props, motor):
    uiuc, _ = props
    dt = pm.Drivetrain(prop=uiuc, motor=motor, esc=pm.generic_esc(), source=pm.KIKUSUI_PWR401L.at(12.0), rho=1.2)
    for d in (0.2, 0.5, 0.8):
        r = pm.rpm_at_duty(dt, d)
        assert float(pm.required_duty(dt, r)) == pytest.approx(d, abs=1e-6)


def test_rewind_keeps_copper_loss(props, motor):
    uiuc, _ = props
    rpm = 8000.0
    losses = []
    for kv in (600, 920, 1500):
        m = motor.with_kv(kv)
        assert m.km == pytest.approx(motor.km)
        dt = pm.Drivetrain(prop=uiuc, motor=m, esc=pm.generic_esc(), source=pm.KIKUSUI_PWR401L.at(20.0), rho=1.2)
        op = pm.at_rpm(dt, rpm)
        losses.append((float(op.p_cu), float(op.p_noload)))
    for l in losses[1:]:
        assert l == pytest.approx(losses[0], rel=1e-6)


def test_voltage_band_ordering(props, motor):
    uiuc, design = props
    spec = Spec()
    lo, rec, hi = voltage_band(motor, pm.generic_esc(), spec, uiuc, design)
    assert lo < rec < hi
    ev = evaluate(motor, pm.generic_esc(), None, spec, uiuc, design)
    assert ev.design["duty"] <= spec.duty_target + 0.01
    assert ev.feasible


def test_air_density_standard():
    assert pm.air_density(15.0, 101_325.0, 0.0) == pytest.approx(1.225, abs=1e-3)
    assert pm.air_density(20.0, 101_325.0, 1.0) < pm.air_density(20.0, 101_325.0, 0.0)


def test_stand_uncertainty_floor():
    from propmotor.stand import TYTO_1585

    # 0.01 N m torque -> +-(0.5% + 0.001) = 10.5 %
    assert TYTO_1585.torque_uncertainty(0.01) / 0.01 == pytest.approx(0.105)


def test_regen_transient_physics(props, motor):
    """Abrupt drop with complementary PWM pumps the bus; diode freewheeling or coasting does not."""
    from propmotor.transient import BusProtection, throttle_drop

    uiuc, _ = props
    dt = pm.Drivetrain(prop=uiuc, motor=motor, esc=pm.generic_esc(), source=pm.DCSource("psu", 12.0, 0.03, 10.0), rho=1.2)
    d0 = float(pm.required_duty(dt, 8000))
    j = 2e-5
    hot = throttle_drop(dt, j, BusProtection("none"), d0, 0.05, t_end=0.3)
    off = throttle_drop(dt, j, BusProtection("diode", complementary_pwm=False), d0, 0.05, t_end=0.3)
    coast = throttle_drop(dt, j, BusProtection("none"), d0, 0.0, t_end=0.3, zero_throttle="coast")
    clamp = throttle_drop(dt, j, BusProtection("clamp", v_clamp=13.5), d0, 0.05, t_end=0.3)
    assert hot.v_peak > 20.0
    assert off.v_peak <= 12.01 and coast.v_peak <= 12.01
    assert clamp.v_peak < 14.0
