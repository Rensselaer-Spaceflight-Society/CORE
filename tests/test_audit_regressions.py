"""Independent conservation, interface and failure-path regression checks."""
import math
import subprocess
import sys
from pathlib import Path
import pytest
from core import gas, thermo, solver
from core.module import ModuleSpec, ModuleError, _TrackedState
from core.combustor import MicroJetCombustor
from core.readiness import blockers
import run

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def state():
    return run.solve()[1]


@pytest.fixture(scope='module')
def combustor():
    return MicroJetCombustor(dict(casing_od_inch=7.25,shaft_tunnel_od_inch=1.4,
        wall_thickness_mm=1.5,pressure_ratio=3.2,compressor_efficiency=.76,
        mass_flow_air_kg_s=.48,target_tit_k=1150,tau_min_s=.0014)).run()


@pytest.mark.parametrize('T',[float('nan'),float('inf'),199.9,1900.1])
def test_properties_reject_out_of_range(T):
    with pytest.raises(gas.GasError): gas.h_air(T)


@pytest.mark.parametrize('eta',[0,-1,1.01,float('nan')])
def test_fuel_balance_rejects_invalid_efficiency(eta):
    with pytest.raises(gas.GasError): gas.far_for_T4(400,1150,eta,43e6)


def test_unreachable_temperature_and_nonconvergence_raise():
    with pytest.raises(gas.GasError): gas.T4_for_far(400,.06,1,100e6)
    with pytest.raises(gas.GasError): gas.far_for_T4(400,1150,.98,43e6,max_iter=0)
    with pytest.raises(gas.GasError): thermo.temperature(1e10)


def test_cycle_enthalpy_and_entropy_conservation(state):
    s=state; f=s['FAR_ratio']; R=s['R_gas_J_kgK']
    assert gas.h_air(s['T03_K'])-gas.h_air(s['T02_K']) == pytest.approx(s['w_comp_J_kg'],rel=1e-10)
    assert gas.h_products(s['T04_K'],f)-gas.h_products(s['T05_K'],f) == pytest.approx(s['w_turb_J_kg'],rel=1e-10)
    Ts=thermo.temperature(gas.h_products(s['T04_K'],f)-s['w_turb_J_kg']/s['eta_t_isen'],f)
    assert thermo.entropy(Ts,f)-thermo.entropy(s['T04_K'],f) == pytest.approx(R*math.log(s['P05_Pa']/s['P04_Pa']),abs=1e-7)


@pytest.mark.parametrize('P0',[150000,400000])
@pytest.mark.parametrize('Cv',[1,.95])
def test_nozzle_energy_and_choking(P0,Cv):
    V,T,P,choked=thermo.nozzle(1050,P0,101325,.02,Cv=Cv)
    assert gas.h_products(1050,.02)-gas.h_products(T,.02) == pytest.approx(V*V/2,rel=1e-9)
    M=V/math.sqrt(thermo.gamma(T,.02)*287.05*T)
    if choked:
        assert M == pytest.approx(1,abs=1e-8)
        assert P >= 101325
    else:
        assert M < 1 and P == 101325


def test_frozen_annuli_and_branch_closure(combustor):
    r=combustor
    for b,f in [('outer',r['f_outer_feed_used']),('inner',1-r['f_outer_feed_used'])]:
        assert r['rho2']*r[f'A_{b}_feed_m2']*r[f'v_{b}_annulus'] == pytest.approx(r['mdot_air']*f,rel=1e-12)
        assert abs(r[b+'_air_balance_error_kg_s']) < 1e-12
    assert r['vap_path_loss_Pa'] <= r['vap_air_pressure_budget_Pa']*(1+1e-10)
    assert r['vap_crimp_dia_mm'] <= r['vap_id_mm']
    assert not r['pressure_loss_validated']


def test_cold_surfaces_and_discharge_total_static(combustor):
    r=combustor; k=r['thermal_scale_ratio']
    for side in ('outer','inner'):
        for face in ('od','id'):
            assert r[f'{side}_liner_{face}_cold_mm']*k == pytest.approx(r[f'{side}_liner_{face}_mm'],rel=1e-12)
        cad=r['cad_geometry'][side+'_liner']
        assert (cad['od']-cad['id'])/2 == pytest.approx(1.5/k,rel=1e-10)
    assert r['exit_T4_total_K'] == 1150
    assert r['exit_T4_K'] < r['exit_T4_total_K']
    assert r['exit_P4_Pa'] < r['exit_P4_total_Pa']
    assert r['exit_rho4']*r['exit_V4_m_s']*r['combustion_annulus_A'] == pytest.approx(r['exit_mdot_kg_s'],rel=1e-8)


def test_m24_does_not_resize_and_preserves_si(state,monkeypatch):
    from modules.m24_combustor_checks import m24_combustor_checks
    def forbidden(*a,**kw): raise AssertionError('M24 attempted another sizing run')
    monkeypatch.setattr(MicroJetCombustor,'run',forbidden)
    out=m24_combustor_checks.spec.run(state)
    assert out['q_dome_W_m2'] == state['comb_q_dome_W_m2']
    assert out['q_dome_W_m2'] > 1e5


def test_m20_uses_changed_cycle_conditions_and_fuel(state,monkeypatch):
    from modules.m20_combustor import m20_combustor
    observed = {}
    original = MicroJetCombustor.run
    def capture(self):
        result = original(self)
        observed.update(result)
        return result
    monkeypatch.setattr(MicroJetCombustor,'run',capture)
    s=dict(state)
    s['T03_K'] += 12
    s['P03_Pa'] *= .95
    s['eta_b_frac'] = .95
    s['LHV_fuel_J_kg'] = 42e6
    s['FAR_ratio'] = gas.far_for_T4(s['T03_K'],s['T04_K'],s['eta_b_frac'],s['LHV_fuel_J_kg'])
    s['mdot_fuel_kg_s'] = s['mdot_kg_s']*s['FAR_ratio']
    m20_combustor.spec.run(s)
    assert observed['T2_K'] == s['T03_K']
    assert observed['P2_Pa'] == s['P03_Pa']
    assert observed['FAR'] == s['FAR_ratio']
    assert observed['mdot_fuel'] == s['mdot_fuel_kg_s']
    assert observed['eta_comb_used'] == .95


def test_rotor_range_distance_and_crossing_are_separate(state):
    from modules.m32_rotordyn import m32_rotordyn
    s=dict(state)
    s['N_operating_min_rpm'] = 10000
    out=m32_rotordyn.spec.run(s)
    assert out['N_crit_margin_frac'] == 0
    assert out['critical_crossed_flag']


def test_readiness_fingerprint_changes_with_model_input(tmp_path):
    from core.readiness import design_fingerprint
    (tmp_path/'config').mkdir()
    p=tmp_path/'config/seed.yaml'
    p.write_text('speed: 1\n')
    before=design_fingerprint(tmp_path)
    p.write_text('speed: 2\n')
    assert design_fingerprint(tmp_path) != before


def test_pump_pressure_distinguishes_absolute_and_differential(state):
    assert state['P_pump_req_Pa']-state['P00_Pa'] == pytest.approx(state['dP_pump_req_Pa'])
    assert state['dP_fuel_line_Pa'] > 0


def test_ngv_area_matches_its_actual_flow_regime(state):
    s=state
    if not s['ngv_choked_flag']:
        V=s['M_ngv_exit_ratio']*math.sqrt(thermo.gamma(s['T_ngv_exit_K'],s['FAR_ratio'],s['R_gas_J_kgK'])*s['R_gas_J_kgK']*s['T_ngv_exit_K'])
        mdot=s['P_ngv_exit_Pa']/(s['R_gas_J_kgK']*s['T_ngv_exit_K'])*V*s['A_throat_ngv_m2']
        assert mdot == pytest.approx(s['mdot_kg_s']*(1+s['FAR_ratio']),rel=1e-9)


def test_blade_force_uses_shared_mass(state):
    s=state
    assert s['F_blade_root_N'] == pytest.approx(s['m_blade_kg']*gas.rpm_to_rad_s(s['N_rpm'])**2*s['r_blade_cg_m'])
    assert s['sigma_root_Pa']*s['A_blade_root_m2'] == pytest.approx(s['F_blade_root_N'])


def test_limits_cover_every_key_and_fail_closed(state):
    limits=run.registry.load_limits()
    assert set(limits) == {c[2] for c in run.CHECKS}
    for key in (run.CHECKS[0][0],):
        bad=dict(state);bad.pop(key)
        with pytest.raises(ValueError): run.check_limits(bad,limits)
        bad[key]=float('inf')
        with pytest.raises(ValueError): run.check_limits(bad,limits)


def test_read_guard_covers_get_iteration_and_mutation():
    v=_TrackedState({'a':1,'secret':2},{'a'},'probe')
    assert dict(v)=={'a':1}
    for action in (lambda:v.get('secret'),lambda:v['secret']):
        with pytest.raises(ModuleError): action()
    with pytest.raises(ModuleError): v['a']=3
    assert not hasattr(v,'update')


def spec(fn,reads,writes):
    return ModuleSpec(fn,reads,writes,'test','test','draft','test','test',0)


def test_module_rejects_infinity():
    m=spec(lambda s:{'x':float('inf')},[],['x'])
    with pytest.raises(ModuleError): m.run({})


def test_self_loop_and_tiny_relaxation_do_not_false_converge():
    m=spec(lambda s:{'x':.5*s['x']+1},['x'],['x'])
    plan=solver.build_plan([m],set())
    assert not plan.is_pure_dag
    s,_=solver.run_plan(plan,{},guesses={'x':0.0})
    assert s['x']==pytest.approx(2,rel=1e-7)
    with pytest.raises(solver.SolverError):
        solver.run_plan(plan,{},guesses={'x':0.0},relax=1e-12,max_block_iters=3)
    with pytest.raises(solver.SolverError): solver.run_plan(plan,{},relax=0)


def test_release_gate_is_blocked_for_unvalidated_design():
    import json
    assert blockers(ROOT)
    r=subprocess.run([sys.executable,'run.py','--release-check'],cwd=ROOT,capture_output=True,text=True)
    assert r.returncode==1
    assert 'NOT FOR MANUFACTURE' in r.stdout
    cad=json.loads((ROOT/'out/cad_dims.json').read_text())
    assert cad['schema_version']==2
    assert cad['release_status']=='PRELIMINARY - NOT FOR MANUFACTURE'
    assert cad['dimensions_mm']['OUTER_LINER_ID_COLD'] < cad['dimensions_mm']['LINER_OUTER_DIA']
    assert cad['hole_counts'] and len(cad['design_fingerprint'])==64


def test_sweep_preserves_design_state_and_total_static():
    from RPM_Sweep_OffDesign import build_design_card,evaluate_off_design_point
    inp=dict(casing_od_inch=4.33,shaft_tunnel_od_inch=1.18,wall_thickness_mm=.5,
        pressure_ratio=2.2,compressor_efficiency=.74,mass_flow_air_kg_s=.23,
        target_tit_k=1123,liner_material='304SS',tau_min_s=.0014)
    card=build_design_card(inp)
    r=evaluate_off_design_point(card['off_design_anchors'],2.2,.23,.74,1123)
    assert r['T4_total_K']==1123
    assert r['T4_static_K']<1123
    assert r['mdot_fuel_kg_s']==pytest.approx(card['v21_full_results']['mdot_fuel'],abs=1e-6)
