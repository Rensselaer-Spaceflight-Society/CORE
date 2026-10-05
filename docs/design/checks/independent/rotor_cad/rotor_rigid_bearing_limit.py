"""High-damping limit check (fork D): as c*omega >> k the damped bending crossing should approach the
undamped synchronous critical with RIGID bearings. Reuses the transfer-matrix code of
rotor_independent.py by text extraction (no core/modules imports). Run from the repo root:
    python rotor_rigid_bearing_limit.py [run_or_snapshot_folder]
Result on cf53eecfed2f: 2 N/um -> 91,187 rpm; 2000 N/um (rigid) -> 77,866 rpm, i.e. 14.5 % above 68 krpm.
"""
from pathlib import Path

here = Path(__file__).with_name('rotor_independent.py').read_text()
head = here.split('# ---------------------------------------------------------------- A  mass properties')[0]
helpers = here.split('# ---------------------------------------------------------------- C  lumped-mass beam')[1].split('def lumped_model')[0]
tmm = here.split('# ---------------------------------------------------------------- D  transfer matrices (synchronous, undamped)')[1] \
          .split('# ---------------------------------------------------------------- validation')[0]
exec(head + helpers + tmm)
for k in (2e6, 2e7, 2e8, 2e9):
    st = tmm_stations(0.001, k=k)  # noqa: F821 (defined by exec)
    r = tmm_roots(st, 60000, 140000, 300)  # noqa: F821
    print(f'TMM undamped synchronous criticals 60-140 krpm, bearing k = {k / 1e6:7.0f} N/um: {[round(v) for v in r]} rpm')
