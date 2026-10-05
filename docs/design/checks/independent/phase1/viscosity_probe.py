"""Probe: re-rate the PD-1 stage at each operating-line state of the latest run with the current
viscosity (turbine_rating.mu_hot, Sutherland air) and with the pre-fix power law 3.5e-5 (T/1000)^0.7,
to show what the correction changed. Read-only; monkeypatches in memory only. Run from the repo root."""
import json, sys
from pathlib import Path
sys.path.insert(0, '.')
from core import cases, candidate, turbine_rating as tr
latest = json.loads(Path('out/pd1-jm85/LATEST.json').read_text())['run_dir'].replace('\\', '/')
line = json.loads((Path('out') / latest / 'operating_line.json').read_text())
case = cases.load_case('pd1-jm85'); recs = cases.case_records(case)
eng = candidate.engine_from_case(case, recs)
suth = lambda T: 1.716e-5 * (T / 273.15) ** 1.5 * (273.15 + 110.4) / (T + 110.4)
prefix_law = lambda T: 3.5e-5 * (T / 1000.0) ** 0.7
tab = {300: 184.6e-7, 800: 369.8e-7, 1000: 424.4e-7}   # Incropera & DeWitt Table A.4 (air, 1 atm)
for T, mu in tab.items():
    print(f'T={T:5d} K  table {mu:.4e}  current mu_hot {tr.mu_hot(T):.4e} ({tr.mu_hot(T)/mu-1:+.1%})  pre-fix law {prefix_law(T):.4e} ({prefix_law(T)/mu-1:+.1%})')
orig = tr.mu_hot
print(' N     Re_N(prefix) Re_R(prefix) Re_N(now) Re_R(now)  eta_tt prefix -> now   flags(now)')
for p in line:
    if 'turbine' not in p: continue
    t, f, s = p['turbine'], p['flows'], p['stations']
    args = (eng.stage, f['m_turbine_kg_s'], s['T41_K'], s['P41_Pa'], p['N_rpm'], f['FAR_mixed'], eng.R)
    tr.mu_hot = prefix_law
    a = tr.rate(*args)
    tr.mu_hot = orig
    b = tr.rate(*args)
    print(f"{p['N_rpm']:6.0f} {a['Re_ngv']:9.0f} {a['Re_rotor']:9.0f} {b['Re_ngv']:10.0f} {b['Re_rotor']:10.0f}   {a['eta_tt']:.4f} -> {b['eta_tt']:.4f}  {b['flags']}")
