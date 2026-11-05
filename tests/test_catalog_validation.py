import pytest

import propmotor as pm
from propmotor.catalog import load_escs, load_motors
from propmotor.selection import TestSpec as Spec
from propmotor.selection import best_esc
from propmotor.validation import load_tests, predict


def test_catalogs_load():
    motors, escs = load_motors(), load_escs(allow_soldering=True)
    assert len(motors) == 11
    assert len(escs) == 7
    assert all(e.pwm_input for e in escs)
    assert len(load_escs()) == 6  # bare boards excluded by default


def test_jp_filter():
    assert all(m.meta.get("jp_available") for m in load_motors(jp_only=True))
    assert all(e.meta.get("jp_available") for e in load_escs(jp_only=True))


def test_every_candidate_has_a_feasible_esc():
    spec = Spec(rho=1.2)
    uiuc, design = pm.apc_8x3_8sf_measured(), pm.apc_8x3_8sf_design()
    for m in load_motors():
        ev = best_esc(m, load_escs(allow_soldering=True), spec, uiuc, design)
        assert ev.feasible, ev.table()


def test_model_matches_manufacturer_thrust_and_current():
    """Regression guard: measured-data prop model + 1st-order motor reproduce independent tests."""
    uiuc = pm.apc_8x3_8sf_measured()
    for t in load_tests():
        p = predict(t, uiuc, rho=1.2)
        if t.thrust_g:
            assert p["thrust_g"] / t.thrust_g == pytest.approx(1.0, abs=0.05), t.label
        if t.throttle == "full":
            assert p["i_motor"] / t.current_a == pytest.approx(1.0, abs=0.07), t.label


def test_apc_theory_overpredicts_thrust():
    apc = pm.apc_8x3_8sf_theory()
    ratios = [predict(t, apc)["thrust_g"] / t.thrust_g for t in load_tests() if t.thrust_g]
    assert min(ratios) > 1.05
