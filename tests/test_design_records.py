"""Records, provenance, fingerprints, case loading and run folders."""
import json
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import records, cases                                   # noqa: E402
from core.records import Record, RecordError, MissingInput, Check   # noqa: E402


def rec(params, sources=()):
    return Record(dict(schema_version=1, record_type='component', component_id='x', title='t',
                       source_documents=[dict(id=s, accessed='2026-10-04') for s in sources], parameters=params))


def test_all_repository_records_validate_and_ids_are_unique():
    import glob
    paths = sorted(glob.glob(os.path.join(records.ROOT, 'data', 'components', '*.yaml')))
    paths.append(os.path.join(records.ROOT, 'data', 'maps', 'gt3076r_compressor.yaml'))
    recs = records.load_records(paths)
    assert {'compressor_wheel', 'turbine_rotor', 'ngv_ring', 'bearings', 'assembly_pd1'} <= set(recs)


@pytest.mark.parametrize('bad', [
    {'a': {'value': 1.0, 'unit': 'furlong', 'basis': 'design'}},                 # unknown unit
    {'a': {'value': None, 'unit': 'mm', 'basis': 'assumption'}},                 # missing value not unresolved
    {'a': {'value': 2.0, 'unit': 'mm', 'basis': 'unresolved'}},                  # unresolved with a value
    {'a': {'value': 2.0, 'unit': 'mm', 'basis': 'supplied'}},                    # supplied without source
    {'a': {'value': 2.5, 'unit': 'count', 'basis': 'design'}},                   # non-integer count
    {'a': {'value': float('nan'), 'unit': 'mm', 'basis': 'design'}},             # non-finite
    {'a': {'value': 1.0, 'unit': 'mm', 'basis': 'design', 'range': [3, 2]}},      # inverted range
])
def test_malformed_parameters_are_rejected(bad):
    with pytest.raises(RecordError):
        rec(bad)


def test_unresolved_value_is_never_zero():
    r = rec({'throat': {'value': None, 'unit': 'mm2', 'basis': 'unresolved', 'note': 'measure'}})
    with pytest.raises(MissingInput):
        r.si('throat')
    assert r.unresolved() == ['throat']


def test_unit_conversion_and_foreign_price_guard():
    r = rec({'d': {'value': 85.0, 'unit': 'mm', 'basis': 'supplied', 'source': 's'},
             'p': {'value': 370.0, 'unit': 'CHF', 'basis': 'supplied', 'source': 's'}}, sources=['s'])
    assert math.isclose(r.si('d'), 0.085)
    with pytest.raises(RecordError):
        r.si('p')     # foreign list price is not a USD quantity


def test_duplicate_component_ids_rejected(tmp_path):
    body = 'schema_version: 1\nrecord_type: component\ncomponent_id: same\ntitle: t\nparameters: {}\n'
    a, b = tmp_path / 'a.yaml', tmp_path / 'b.yaml'
    a.write_text(body); b.write_text(body)
    with pytest.raises(RecordError):
        records.load_records([a, b])


def test_check_unknown_is_never_pass():
    c = Check.compare('x', None, '<=', 1.0)
    assert c.status == 'unknown'
    with pytest.raises(ValueError):
        Check('y', 'pass', None)
    assert Check.compare('z', 2.0, '<=', 1.0).status == 'fail'


def test_fingerprint_changes_with_content_not_with_time(tmp_path):
    f = tmp_path / 'd.yaml'
    f.write_bytes(b'a: 1\n')
    fp1 = records.fingerprint([f])
    fp2 = records.fingerprint([f])
    assert fp1 == fp2                       # deterministic; no timestamp
    f.write_bytes(b'a: 2\n')
    assert records.fingerprint([f]) != fp1
    f.write_bytes(b'a: 1\r\n')              # line endings normalised
    assert records.fingerprint([f]) == fp1


def test_case_loading_and_identity():
    case = cases.load_case('pd1-jm85')
    recs = cases.case_records(case)
    files = [p.name for p in cases.design_files(case, recs)]
    for must in ('pd1-jm85.yaml', 'gt3076r_compressor_digitized.csv', 'turbine_jetmax_tw85.yaml', 'engine_match.py',
                 'pd1_adjustments.yaml', 'oct02_parts_budget.csv', 'signals.yaml', 'turbine_jetmax_tw70.yaml'):
        assert must in files      # budget, systems and alternative-stage records change run outputs too
    with pytest.raises(cases.CaseError):
        cases.load_case('does-not-exist')


def test_run_folder_failure_marks_previous_result_stale(tmp_path):
    ok = cases.RunFolder('demo', 'a' * 64, tmp_path)
    ok.write_json('x.json', {'v': 1})
    final = ok.commit()
    latest = json.loads((tmp_path / 'demo' / 'LATEST.json').read_text())
    assert latest['status'] == 'success' and final.exists()
    bad = cases.RunFolder('demo', 'b' * 64, tmp_path)
    bad.fail(RuntimeError('boom'))
    latest = json.loads((tmp_path / 'demo' / 'LATEST.json').read_text())
    assert latest['status'] == 'failed' and latest['previous_success_is_current'] is False
    assert (tmp_path / 'demo' / ('a' * 12) / 'x.json').exists()        # old result kept, not overwritten
    assert not (tmp_path / 'demo' / ('b' * 12)).exists()               # failed run never promoted


def test_run_paths_cannot_escape_output_root(tmp_path):
    with pytest.raises(cases.CaseError):
        cases.RunFolder('../escape', 'a' * 64, tmp_path)
    with pytest.raises(cases.CaseError):
        cases.RunFolder('demo', '../escape', tmp_path)


def test_seed_provenance_labels_carry_the_record_basis():
    import re
    from core import candidate
    case = cases.load_case('pd1-jm85')
    recs = cases.case_records(case)
    eng = candidate.engine_from_case(case, recs)
    dp = dict(N_rpm=68000.0, T04_K=850.0, beta=0.6, thrust_N=40.0,
              stations=dict(P2_Pa=1e5, T3_K=334.0, P3_Pa=1.5e5, P31_Pa=1.47e5, P4_Pa=1.43e5, T5_K=810.0, P5_Pa=1.13e5,
                            P7_Pa=1.11e5),
              flows=dict(m_air_kg_s=0.2, m_comb_air_kg_s=0.196, m_fuel_kg_s=0.0027),
              losses=dict(combustor_frac=0.025), compressor=dict(w_J_kg=46000.0, PR=1.5, eta=0.76),
              turbine=dict(w_J_kg=45000.0, eta_tt=0.84, M1=0.4, T1_K=820, P1_Pa=130000),
              powers=dict(P_compressor_W=9200, P_bearings_W=100))
    seeds = candidate.candidate_seeds(case, recs, eng, dp)
    by_id = {r.id: r for r in recs.values()}
    checked = 0
    for key, (_, label) in seeds.items():
        m = re.match(r'record (\w+)\.(\w+) \(([^)]+)\)', label)
        if m:
            rid, pname, basis = m.groups()
            assert by_id[rid].param(pname)['basis'].lower() in basis.lower(), (key, label)
            checked += 1
    assert checked > 30
    # estimates behind the rotor inertias and the unresolved seat fit must not read as supplier data
    assert seeds['cw_Ip_kg_m2'][1].endswith('(assumption)') and seeds['shaft_comp_seat_d_m'][1].endswith('(assumption)')


def test_assumptions_register_includes_case_level_inputs():
    import run_case
    case = cases.load_case('pd1-jm85')
    rows = run_case.assumptions_register(cases.case_records(case), case)
    case_rows = {(r['component'], r['parameter']): r['value'] for r in rows if r['role'] == 'case'}
    assert case_rows[('pd1-jm85.engine', 'comb_loss_design')] == 0.025
    assert ('pd1-jm85.rotor_support', 'k_support_N_m') in case_rows
    assert ('pd1-jm85.engine', 'nozzle_Cd') in case_rows and ('pd1-jm85.engine', 'LHV_J_kg') in case_rows


def _snapshot_tool(tmp_path, case_id='baseline-250N'):
    """make_design_snapshot.py pointed at a scratch output/results root, with one current run."""
    import importlib.util
    from core.records import file_sha256
    spec = importlib.util.spec_from_file_location('snap', os.path.join(records.ROOT, 'scripts', 'make_design_snapshot.py'))
    snap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(snap)
    snap.ROOT = tmp_path
    case = cases.load_case(case_id)
    opts = {'robustness': False}
    run = tmp_path / 'out' / case_id / 'run'
    run.mkdir(parents=True)
    (run / 'limits.json').write_text('[]')
    (run / 'candidate_checks.json').write_text('[]')
    manifest = dict(design_fingerprint=cases.case_fingerprint(case, cases.case_records(case), extra=opts),
                    release_status='PRELIMINARY - NOT FOR MANUFACTURE', run_options=opts,
                    generated_files={n: file_sha256(run / n) for n in ('limits.json', 'candidate_checks.json')})
    (run / 'manifest.json').write_text(json.dumps(manifest))
    (tmp_path / 'out' / case_id / 'LATEST.json').write_text(
        json.dumps(dict(case_id=case_id, run_dir=f'{case_id}/run', status='success')))
    (tmp_path / 'docs' / 'design' / 'results').mkdir(parents=True)
    return snap, run, tmp_path / 'docs' / 'design' / 'results' / case_id


def test_snapshot_accepts_current_run_without_hashing_its_own_manifest(tmp_path):
    snap, run, dst = _snapshot_tool(tmp_path)
    snap.main(['baseline-250N'])
    assert (dst / 'SUMMARY.md').exists() and (dst / 'manifest.json').exists()


def test_snapshot_tables_keep_small_values_distinguishable(tmp_path):
    snap, _, _ = _snapshot_tool(tmp_path)
    assert snap.fmt(0.0014) != snap.fmt(0.0012)        # residence time vs its 1.2 ms limit
    assert snap.fmt(0.003048) == '0.003048'


def test_snapshot_rejects_tampered_or_missing_listed_output(tmp_path):
    snap, run, dst = _snapshot_tool(tmp_path)
    (run / 'limits.json').write_text('[{}]')
    with pytest.raises(SystemExit, match='hash mismatch'):
        snap.main(['baseline-250N'])
    snap, run, dst = _snapshot_tool(tmp_path / 'second')
    (run / 'candidate_checks.json').unlink()           # listed in the manifest but gone
    with pytest.raises(SystemExit, match='missing'):
        snap.main(['baseline-250N'])
    assert not dst.exists()                            # nothing half-written


def test_compose_seed_records_provenance_and_rejects_nonfinite():
    case = cases.load_case('pd1-jm85')
    seed, prov = cases.compose_seed(case, {'N_rpm': (1.0, 'test')})
    assert prov['N_rpm'] == 'test' and prov['T00_K'] == 'seed_base'
    with pytest.raises(cases.CaseError):
        cases.compose_seed(case, {'N_rpm': (float('inf'), 'bad')})
