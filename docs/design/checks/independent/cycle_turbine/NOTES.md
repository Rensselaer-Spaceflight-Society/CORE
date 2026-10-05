# Fork A — cycle closure, turbine mean line, R3, Reynolds data (R5)

Run from the repository root (`C:\Users\andyc\OneDrive\Desktop\CORE\github-core`). Each script takes an
optional results folder (default `docs/design/results/pd1-jm85`), prints one line per comparison and exits 1
on any unexplained difference above its tolerance. Saved outputs: `*.out` next to each script.

```
python <dir>/r3_turbine_check.py   [results_dir] [pre_review_run_dir=out/pd1-jm85/af33609c34b6]
python <dir>/cycle_closure.py      [results_dir]
python <dir>/reynolds_validity.py  [results_dir]
```

Independence: only `core.gas` property functions (cp/h of air and the products surrogate) are imported,
through `indep_props.py`. Entropy (quadrature), inversions, isentropic relations, Soderberg losses,
continuity, Euler work, mixing, FAR, bearing/windage power, jet pipe, nozzle and thrust are re-implemented.
Inputs come from `config/cases/pd1-jm85.yaml` and `data/components/*.yaml`; the run's echoed inputs are
compared against them.

Results on run cf53eecfed2f (2026-10-04, fork A):
- R3 residuals at 68 krpm: energy 0.0000 J/kg, Euler (passage and mixed plane) exact, exit continuity 0 %,
  eta_tt and T05 reproduced to 1e-7 %. Pre-review run af33609c34b6: exit state short by -2222.3 J/kg
  (= w_Euler - w, the tip-leakage debit) -> R3 defect confirmed and fixed.
- Independent re-rating of the stage with the documented method reproduces every reported turbine output
  (triangles, losses, Re, eta_tt 0.85115, psi 0.7312, phi 0.5146, reaction 0.4866) to < 1e-6 %.
- Cycle closes at the design point and at all 11 operating-line speeds (worst 2e-11 relative).
- Viscosity used for the Soderberg Reynolds correction (3.5e-5 (T/1000)^0.7) is 18-21 % below air
  (Sutherland) at 785-1000 K. With air viscosity the rotor Re falls below the 2e4 flag at 56-66 krpm
  (6 of 7 steady-range speeds) instead of 56-58 krpm (2 of 7). The 2e4 bound is unsourced; Soderberg's
  basis is Re 1e5 (all steady points are at 0.19-0.24 of it).

After the verification fixes (final snapshot `4a7560bfca63`): the scripts use Sutherland's law as the model
viscosity (the repository now does too) and keep the pre-fix power law only for comparison. All three scripts
exit 0 on the final snapshot; see the `*.out` files. Final design point: w 45,465.25 J/kg, eta_tt 0.84625,
T05 797.587 K; rotor Re 15,555 (56 krpm) to 20,024 (68 krpm), flagged at 56-66 krpm.
