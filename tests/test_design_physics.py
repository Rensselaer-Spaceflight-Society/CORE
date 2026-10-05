"""Compressor map, turbine rating, matching, diffuser and property-inversion checks."""
import math
import os
import random
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import gas, thermo, diffuser                                        # noqa: E402
from core.compressor_map import default_map, MapDomainError, MapOffsets       # noqa: E402
from core.records import load_record                                          # noqa: E402
from core.turbine_rating import (StageGeometry, rate, TurbineLimit, soderberg,  # noqa: E402
                                 stage_from_records)
from core.engine_match import (EngineDefinition, MechanicalLosses, Bearing,    # noqa: E402
                               match_speed, solve_from_guess, _evaluate)


@pytest.fixture(scope='module')
def cmap():
    return default_map()


@pytest.fixture(scope='module')
def stage():
    t = load_record('data/components/turbine_jetmax_tw85.yaml')
    n = load_record('data/components/ngv_jetmax_ngv85.yaml')
    return stage_from_records(t, n)


# ------------------------------------------------------------------- properties
def test_newton_inversions_match_bisection():
    rnd = random.Random(7)
    for _ in range(300):
        T, f = rnd.uniform(260, 1800), rnd.uniform(0, 0.05)
        h = gas.h_products(T, f)
        assert abs(thermo.temperature_fast(h, f) - thermo.temperature(h, f)) < 1e-6
        pr = rnd.uniform(0.4, 3.5)
        try:
            ref = thermo.isentropic_temperature(T, pr, f)
        except gas.GasError:
            continue
        assert abs(thermo.isentropic_temperature_fast(T, pr, f) - ref) < 1e-6


# ------------------------------------------------------------------- compressor map
def test_corrected_condition_round_trip(cmap):
    for T, P in ((288.15, 100300.0), (308.15, 95000.0)):
        q = cmap.corrected_flow(0.21, T, P)
        assert math.isclose(cmap.actual_flow(q, T, P), 0.21, rel_tol=1e-12)
    # 545 R / 28.4 inHg reference: hotter inlet lowers corrected speed
    assert cmap.corrected_speed(66000, 302.78) == pytest.approx(66000, rel=1e-4)
    assert cmap.corrected_speed(66000, 288.15) > 66000


def test_map_domain_is_enforced(cmap):
    with pytest.raises(MapDomainError):
        cmap.point(50000.0, 0.5)          # below the lowest digitized line
    with pytest.raises(MapDomainError):
        cmap.point(150000.0, 0.5)         # above the highest
    with pytest.raises(MapDomainError):
        cmap.point(70000.0, 1.05)         # beyond choke end
    with pytest.raises(MapDomainError):
        cmap.point(70000.0, -0.01)        # beyond surge end


def test_map_points_reproduce_digitized_lines_and_are_physical(cmap):
    for ln in cmap.lines:
        q, pr, eta = cmap.point(ln.n_corr, 0.0)
        assert math.isclose(q, ln.q[0], rel_tol=1e-9) and math.isclose(pr, ln.pr[0], rel_tol=1e-9)
        qs = [cmap.point(ln.n_corr, b)[0] for b in (0, 0.25, 0.5, 0.75, 1.0)]
        assert all(b > a for a, b in zip(qs, qs[1:]))      # flow rises from surge to choke
        for b in (0, 0.3, 0.6, 1.0):
            assert 0.55 <= cmap.point(ln.n_corr, b)[2] <= 0.78
    # the published DP-2 point (0.30 kg/s, PR 1.63) is NOT on the 66 krpm line of this map
    q = cmap.corrected_flow(0.30, 288.15, 101325 * 0.99)
    with pytest.raises(MapDomainError):
        cmap.beta_for_flow(cmap.corrected_speed(66000, 288.15), q)


def test_map_offsets_are_explicit_and_do_not_mutate_data():
    base = default_map()
    off = default_map(MapOffsets(flow_scale=0.95, eta_delta=-0.03))
    a, b = base.point(80000, 0.5), off.point(80000, 0.5)
    assert math.isclose(b[0], 0.95 * a[0]) and math.isclose(b[2], a[2] - 0.03)
    assert base.point(80000, 0.5) == a


# ------------------------------------------------------------------- turbine rating
def test_soderberg_hand_value():
    # deflection 90 deg, chord/height 1/3, nozzle: z* = 0.04 (1 + 1.5 x 0.81) = 0.0886
    z = soderberg(90.0, 1.0, 3.0, 'nozzle')
    assert math.isclose(z, (1.0886) * (0.993 + 0.007) - 1.0, rel_tol=1e-9)


def test_turbine_viscosity_matches_tabulated_air():
    # Independent reference: air at 1 atm, Incropera & DeWitt, Fundamentals of Heat and Mass
    # Transfer, Table A.4 (N s/m2). The Reynolds number sets the Soderberg correction and the
    # validity flag, so a 20 % viscosity error moves both.
    from core.turbine_rating import mu_hot
    for T, mu in ((300.0, 184.6e-7), (800.0, 369.8e-7), (1000.0, 424.4e-7)):
        assert abs(mu_hot(T) / mu - 1) < 0.04


def test_rating_conserves_energy_and_mass(stage):
    r = rate(stage, 0.2, 1000.0, 140000.0, 66000.0, 0.018)
    assert abs(r['energy_residual_J_kg']) < 1e-6          # Euler work = h01 - h02 (passage)
    # independent recomputation of Euler work from the reported velocity triangle
    U = r['U_mean_m_s']
    Ct1 = r['C1_m_s'] * math.sin(math.radians(r['alpha1_deg']))
    Ct2 = U + r['W2_m_s'] * math.sin(math.radians(r['beta2_deg']))
    assert math.isclose(U * (Ct1 - Ct2) * r['tip_work_factor'], r['w_J_kg'], rel_tol=1e-9)
    rho1 = r['P1_Pa'] / (287.05 * r['T1_K'])
    assert math.isclose(rho1 * r['C1_m_s'] * r['A_ngv_throat_m2'], 0.2, rel_tol=1e-6)


def test_rating_rejects_flow_beyond_choke_and_keeps_geometry(stage):
    before = stage.as_dict()
    with pytest.raises(TurbineLimit):
        rate(stage, 0.40, 1150.0, 150000.0, 66000.0, 0.02)
    assert stage.as_dict() == before                      # frozen dataclass: geometry untouched


@pytest.mark.parametrize('clearance', [0.0, 0.00035, 0.0005])
def test_penalised_turbine_exit_closes_mass_energy_and_euler(stage, clearance):
    far, mdot = 0.018, 0.2
    r = rate(stage.with_(tip_clearance_m=clearance), mdot, 1000, 140000, 66000, far)
    m = r['mixed_exit']
    assert m['P_static_Pa'] / (287.05 * m['T_static_K']) * m['Cx_m_s'] * m['annulus_area_m2'] == pytest.approx(mdot)
    assert gas.h_products(r['T02_K'], far) == pytest.approx(
        gas.h_products(m['T_static_K'], far) + m['C_m_s'] ** 2 / 2, abs=1e-4)
    Ct1 = r['C1_m_s'] * math.sin(math.radians(r['alpha1_deg']))
    assert r['U_mean_m_s'] * (Ct1 - m['Ct_m_s']) == pytest.approx(r['w_J_kg'])
    assert thermo.pressure(r['T02_K'], m['T_static_K'], m['P_static_Pa'], far) == pytest.approx(r['P02_Pa'])
    if clearance == 0:
        assert m['T_static_K'] == pytest.approx(r['T2_K'], abs=1e-6)
        assert m['C_m_s'] == pytest.approx(r['C2_m_s'], abs=1e-6)


def test_supplied_inlet_metal_angle_is_used():
    t = load_record('data/components/turbine_jetmax_tw85.yaml')
    n = load_record('data/components/ngv_jetmax_ngv85.yaml')
    t.parameters['rotor_inlet_metal_angle'] = dict(value=-8, unit='deg', basis='design')
    assert stage_from_records(t, n).beta1_metal_deg == pytest.approx(-8)


def test_local_solvers_reject_out_of_domain_roots(stage, cmap, monkeypatch):
    from types import SimpleNamespace
    from core.engine_match import verify_point
    eng = _engine(stage, cmap)
    monkeypatch.setattr('scipy.optimize.root', lambda *a, **kw: SimpleNamespace(x=(1.01, 900), success=True))
    assert not any(r['success'] for r in verify_point(eng, {'N_rpm': 66000}))
    monkeypatch.setattr('scipy.optimize.root', lambda *a, **kw: SimpleNamespace(x=(0.6, eng.T04_search_max_K + 1), success=True))
    assert solve_from_guess(eng, 66000, 0.6, 900) is None


def test_robustness_does_not_pass_invalid_turbine_correlation():
    from core.robustness import screens
    p = dict(T04_K=900, compressor=dict(SM_flow=0.3, eta_confidence='medium'),
             turbine=dict(ngv_flow_fraction_of_max=0.7, rotor_flow_fraction_of_max=0.7,
                          flags=['negative rotor reaction']))
    assert 'negative rotor reaction' in screens(p, 1150)


def _pt(T04=900.0, flags=(), conf='medium'):
    return dict(T04_K=T04, compressor=dict(SM_flow=0.3, eta_confidence=conf),
                turbine=dict(ngv_flow_fraction_of_max=0.7, rotor_flow_fraction_of_max=0.7, flags=list(flags)))


def test_model_validity_is_unresolved_not_failed_and_never_feasible():
    from core.robustness import screens, status_of
    assert status_of(screens(_pt(), 1150)) == 'feasible'
    assert status_of(screens(_pt(flags=['Reynolds number outside range']), 1150)) == 'unresolved'
    assert status_of(screens(_pt(conf='low'), 1150)) == 'unresolved'
    assert status_of(screens(None, 1150, 'outside digitized lines')) == 'unresolved'
    # a physical exceedance stays a failure even where the model is also outside its range
    assert status_of(screens(_pt(T04=1300.0, flags=['Reynolds number outside range']), 1150)) == 'fails'
    assert status_of(screens(None, 1150, 'no sign change')) == 'fails'


def test_threshold_reports_failure_just_past_the_boundary(monkeypatch):
    # loss multiplier: feasible below 2, T04 screen exceeded from 2 to 5, no match beyond 5
    from types import SimpleNamespace
    from core import robustness as rb

    def fake_solve(spec, N, guess, T0, P0):
        s = (spec.get('stage') or {}).get('loss_scale', 1.0)
        if s >= 5.0:
            return None, 'scan', 'no sign change', None
        return _pt(T04=900.0 if s < 2.0 else 1200.0), 'scan', None, None
    monkeypatch.setattr(rb, 'build', lambda case, recs, base_eng, spec, N: spec)
    monkeypatch.setattr(rb, '_solve', fake_solve)
    stage = SimpleNamespace(ngv_throat=lambda: (1.5e-3, 65.0), A_ngv_exit_m2=3.5e-3,
                            rotor_throat=lambda: (1.7e-3, -58.0), A_rotor_m2=3.3e-3)
    rows = rb.threshold_search(dict(ambient=dict(T0_K=288.15, P0_Pa=101325.0)), None,
                               SimpleNamespace(stage=stage), dict(N_rpm=68000.0), 1150.0)
    row = next(r for r in rows if r['parameter'].startswith('turbine loss multiplier'))
    assert row['boundary'] == pytest.approx(2.0, abs=1e-3)
    assert row['failure_beyond'].startswith('T04 1200 K')            # not the 'no steady match' at 10x


def test_range_checks_do_not_pass_on_extrapolated_points():
    import run_case
    case = dict(operating=dict(steady_range_rpm=[56000, 68000]), engine=dict(T04_screen_max_K=1150.0))

    def point(N, flags):
        return dict(N_rpm=N, converged=True, T04_K=850.0, compressor=dict(SM_flow=0.5),
                    turbine=dict(flags=flags, ngv_flow_fraction_of_max=0.7, rotor_flow_fraction_of_max=0.7))
    state = dict(nozzle_mass_residual_ratio=0.0, t_tip_clear_m=3.5e-4)
    dp = dict(residuals=dict(r_mass=0.0, r_power=0.0))
    diff = dict(throat_open_ratio=0.8, turn_loss_frac=0.01)
    rd = dict(separation_frac=0.3, unbalance=dict(response=[]))
    names = ('steady self-sustaining match at every rated speed in range', 'turbine correlation validity over steady range',
             'max T04 over steady range', 'min surge margin (flow) over steady range')
    clean = {c.name: c.status for c in run_case.candidate_extra_checks(
        state, dp, [point(56000, []), point(68000, [])], diff, rd, case)}
    assert all(clean[n] == 'pass' for n in names)
    low_re = {c.name: c.status for c in run_case.candidate_extra_checks(
        state, dp, [point(56000, ['Reynolds number outside range']), point(68000, [])], diff, rd, case)}
    assert all(low_re[n] == 'unknown' for n in names)                # neither pass nor engine failure


def test_fixed_nozzle_pressure_thrust_uses_geometric_exit_area():
    from modules.m40_nozzle import _fixed_nozzle
    s = dict(R_gas_J_kgK=287.05, mdot_kg_s=0.2, mdot_fuel_kg_s=0.004, A8_fixed_m2=0.002,
             nozzle_Cd_ratio=0.8, T05_K=900, op_P07_Pa=300000, P00_Pa=101325, Cv_nozzle_ratio=0.97)
    r = _fixed_nozzle(s)
    V, T, P, choked = thermo.nozzle(900, 300000, 101325, 0.02, Cv=0.97)
    assert choked
    assert r['F_gross_N'] == pytest.approx(0.204 * V + 0.002 * (P - 101325))


def test_throat_override_sets_angle_by_cosine_rule(stage):
    A = 0.5 * stage.A_ngv_exit_m2
    s2 = stage.with_(A_ngv_throat_m2=A)
    assert math.isclose(s2.ngv_throat()[1], 60.0, rel_tol=1e-9)
    with pytest.raises(ValueError):
        stage.with_(A_ngv_throat_m2=1.2 * stage.A_ngv_exit_m2).ngv_throat()


# ------------------------------------------------------------------- matching
def _engine(stage, cmap, D8=0.054):
    mech = MechanicalLosses(bearings=[Bearing('f', 10, 26), Bearing('r', 10, 26)])
    return EngineDefinition('test', stage, cmap, math.pi / 4 * D8 ** 2, 2.5e-5, comb_loss_design=0.025,
                            duct_loss_design=0.02, mech=mech)


def test_inner_power_balance_finds_root_next_to_choke(monkeypatch):
    # Power balance crosses zero at 735 K but the stage chokes from 740 K: the coarse T04
    # grid only sees a negative residual and then infeasible points.
    from types import SimpleNamespace
    from core import engine_match as em

    def fake_eval(eng, N, beta, T, T0, P0):
        if T >= 740.0:
            raise TurbineLimit('NGV throat choked')
        return dict(r_power=(T - 735.0) / 100.0)
    monkeypatch.setattr(em, '_evaluate', fake_eval)
    eng = SimpleNamespace(cmap=SimpleNamespace(operate=lambda *a: dict(T_out_K=334.0)), inlet_loss_ref=0.01,
                          R=287.05, T04_search_max_K=1500.0)
    T, ev = em._inner_T04(eng, 68000.0, 0.3, 288.15, 101325.0)
    assert T == pytest.approx(735.0, abs=1e-4) and ev['r_power'] == pytest.approx(0.0, abs=1e-6)


def test_match_closes_both_residuals_with_zero_starter(stage, cmap):
    eng = _engine(stage, cmap)
    r = match_speed(eng, 66000, n_scan=9)
    assert r['status'] == 'matched' and r['branches']
    b = r['branches'][0]
    assert abs(b['residuals']['r_mass']) < 1e-6 and abs(b['residuals']['r_power']) < 1e-6
    assert b['powers']['P_starter_W'] == 0.0
    # independent re-evaluation of the solved point
    ev = _evaluate(eng, 66000, b['beta'], b['T04_K'], 288.15, 101325.0)
    assert abs(ev['r_mass']) < 1e-6 and abs(ev['r_power']) < 1e-6
    # same root from a different start
    p2 = solve_from_guess(eng, 66000, min(b['beta'] + 0.1, 0.95), b['T04_K'] + 120)
    assert p2 is not None and abs(p2['T04_K'] - b['T04_K']) < 1e-3


def test_smaller_nozzle_raises_T04_and_moves_toward_surge(stage, cmap):
    a = match_speed(_engine(stage, cmap, 0.058), 66000, n_scan=9)['branches'][0]
    b = solve_from_guess(_engine(stage, cmap, 0.050), 66000, a['beta'], a['T04_K'])
    assert b is not None
    assert b['T04_K'] > a['T04_K'] and b['beta'] < a['beta'] and b['thrust_N'] > a['thrust_N']


def test_unmatched_speed_is_reported_not_recycled(stage, cmap):
    r = match_speed(_engine(stage, cmap), 40000)
    assert r['status'] == 'outside_map' and not r['branches']
    tiny = _engine(stage, cmap, 0.020)                    # absurd nozzle: no steady match
    r = match_speed(tiny, 66000, n_scan=7)
    assert r['status'] == 'no_match' and r['branches'] == []


# ------------------------------------------------------------------- diffuser
def test_diffuser_throat_continuity_and_flags():
    d = diffuser.design(0.2, 335.0, 150000.0, 0.07613, 0.00575, 60.0, 175.0, 1.08, 0.126, 19, 1.04, 0.7, 12, 0.6, 0.5,
                        287.05, 1.5)
    assert d['throat_open_ratio'] < 1 and d['area_ratio'] > 2.5
    assert d['P_exit_static_Pa'] / (287.05 * d['T_exit_static_K']) * d['C_exit_m_s'] * d['exit_flow_area_m2'] == pytest.approx(0.2)
    rho_th_V = 0.2 / d['A_throat_m2']
    assert rho_th_V > 0
    # the opening ratio is independent of vane count (both scale with 1/Z); a low throat Mach target
    # needs more area than the leading-edge pitch provides and must be flagged
    slow = diffuser.design(0.2, 335.0, 150000.0, 0.07613, 0.00575, 60.0, 175.0, 1.08, 0.126, 19, 1.04, 0.35)
    assert slow['throat_open_ratio'] > 1 and slow['flags']
    with pytest.raises(ValueError):
        diffuser.design(0.2, 335.0, 150000.0, 0.07613, 0.00575, 60.0, 175.0, 0.9, 0.126, 19)


# ------------------------------------------------------------------- independent property reference (NIST-JANAF)
def test_air_fit_against_nist_janaf_species_mixture():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs', 'design', 'checks'))
    import gas_property_audit as ga
    for T in (300, 500, 800, 1000, 1300, 1500):
        assert abs(gas.cp_air(T) / ga.mixture_cp_mass(ga.AIR, T) - 1) < 0.003


def test_products_surrogate_deviation_is_bounded_and_reported():
    import gas_property_audit as ga
    for f in (0.0139, 0.022):
        for T in (800, 1000, 1150):
            err = gas.cp_products(T, f) / ga.mixture_cp_mass(ga.products(f), T) - 1
            assert -0.03 < err < 0.0      # surrogate is LOW by 1-2 %: documented, not hidden
