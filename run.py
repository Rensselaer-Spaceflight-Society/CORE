#!/usr/bin/env python3
"""
CORE engine design pipeline.

    python run.py               solve the design point and write out/
    python run.py --status      maturity board: who owns what, how done it is
    python run.py --graph       dependency graph and execution order
    python run.py --trace       show the solver working, including loop passes

The whole design regenerates from config/seed.yaml in under a second. If you
want to know what happens when the turbine inlet temperature drops 50 K, change
one number and run it again.
"""

from __future__ import annotations
import argparse
import importlib
import json
import math
import os
import pkgutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import registry, solver          # noqa: E402
from core.module import REGISTERED         # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")


def load_all_modules():
    import modules
    for _, name, _ in pkgutil.iter_modules(modules.__path__):
        importlib.import_module(f"modules.{name}")
    return list(REGISTERED.values())


def solve(trace=False):
    specs = load_all_modules()
    seed = registry.load_seed()
    limits = registry.load_limits()
    guesses = registry._coerce_numbers(registry.load_yaml("initial_guess.yaml"), "config/initial_guess.yaml")

    seeded = set(seed) | set(limits)
    plan = solver.build_plan(specs, seeded)

    state = dict(seed)
    state.update(limits)

    state, log = solver.run_plan(plan, state, guesses=guesses, trace=trace)

    return plan, state, limits, log


CHECKS = [
    ("U_turb_tip_m_s", "<=", "tip_speed_turb_max_m_s", "turbine tip speed"),
    # (state key, comparison, limit key, human message)
    ("T04_K",              "<=", "T04_max_K",              "turbine inlet temperature"),
    ("U2_m_s",             "<=", "U2_max_m_s",             "impeller tip speed"),
    ("M1s_rel_ratio",      "<=", "M1s_rel_max_ratio",      "inducer shroud relative Mach"),
    ("blade_stress_speed_margin_ratio", ">=", "burst_margin_min_ratio", "blade stress speed screening"),
    ("AN2_m2_rpm2",        "<=", "AN2_max_m2_rpm2",        "turbine AN^2"),
    ("DN_mm_rpm",          "<=", "DN_max_mm_rpm",          "bearing DN"),
    ("T_liner_wall_K",     "<=", "T_liner_wall_max_K",     "combustor liner wall temperature"),
    ("N_crit_margin_frac", ">=", "N_crit_margin_min_frac", "critical speed separation"),
    ("q_dome_W_m2",        "<=", "q_dome_max_W_m2",        "combustor dome heat flux"),
    ("J_primary_ratio",    ">=", "J_primary_min_ratio",    "primary jet momentum ratio (low)"),
    ("J_primary_ratio",    "<=", "J_primary_max_ratio",    "primary jet momentum ratio (high)"),
    ("dil_pen_ratio",      "<=", "dil_pen_max_ratio",      "dilution jet penetration"),
    ("tau_res_s",          ">=", "tau_res_min_s",          "combustor residence time"),
    ("hole_K_ratio",       ">=", "hole_K_min_ratio",       "liner hole pressure-drop coefficient"),
    ("casing_fit_margin_m", ">=", "casing_fit_margin_min_m", "combustor clearance in the casing"),
]


def check_limits(state, limits):
    rows = []
    for key, op, lim_key, label in CHECKS:
        if key not in state or lim_key not in limits:
            raise ValueError(f"missing mandatory limit input: {key} / {lim_key}")
        v, lim = state[key], limits[lim_key]
        if not all(isinstance(x,(int,float)) and math.isfinite(x) for x in (v,lim)):
            raise ValueError(f"nonfinite limit input: {key} / {lim_key}")
        ok = (v <= lim) if op == "<=" else (v >= lim)
        rows.append((label, key, v, op, lim, ok))
    return rows


def fmt(v):
    if isinstance(v, bool):
        return "yes" if v else "no"
    if abs(v) >= 1e5 or (v != 0 and abs(v) < 1e-3):
        return f"{v:.4g}"
    return f"{v:,.4f}".rstrip("0").rstrip(".")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true", help="module maturity board")
    ap.add_argument("--graph", action="store_true", help="dependency graph and order")
    ap.add_argument("--trace", action="store_true", help="show the solver working")
    ap.add_argument('--report-only',action='store_true',help='write PRELIMINARY diagnostics even if limits fail')
    ap.add_argument('--release-check',action='store_true',help='require limits and current reviewed evidence')
    args = ap.parse_args()
    if args.report_only and args.release_check:
        ap.error('--report-only cannot be combined with --release-check')

    if args.status:
        specs = load_all_modules()
        print("\nMODULE MATURITY BOARD\n" + "=" * 78)
        print(f"{'module':<22}{'owner':<10}{'second':<10}{'status':<10}{'title'}")
        print("-" * 78)
        counts = {"stub": 0, "draft": 0, "verified": 0}
        for m in sorted(specs, key=lambda x: (x.tier, x.name)):
            counts[m.status] += 1
            mark = {"stub": "..", "draft": "->", "verified": "OK"}[m.status]
            print(f"{m.name:<22}{m.owner:<10}{str(m.second or '-'):<10}{mark} {m.status:<9}{m.title}")
        print("-" * 78)
        total = sum(counts.values())
        print(f"{total} modules: {counts['verified']} verified, "
              f"{counts['draft']} draft, {counts['stub']} stub")
        unstaffed = [m.name for m in specs if not m.second]
        if unstaffed:
            print(f"\nNO SECOND ASSIGNED (bus factor 1): {', '.join(unstaffed)}")
        return

    plan, state, limits, log = solve(trace=args.trace)

    if args.graph:
        print("\nEXECUTION ORDER\n" + "=" * 60)
        print(plan.describe())
        print("\nCOUPLED GROUPS (genuine circular dependencies)")
        found = False
        for b in plan.blocks:
            if len(b) > 1:
                found = True
                print("  " + " <-> ".join(m.name for m in b))
        if not found:
            print("  none -- the graph is a pure DAG")
        print()

    if args.trace:
        print("\nSOLVER TRACE\n" + "=" * 60)
        for line in log:
            print(line)

    os.makedirs(OUT, exist_ok=True)

    # ---- station table -------------------------------------------------
    stations = [
        ("0  ambient",            "T00_K", "P00_Pa"),
        ("2  compressor inlet",   "T02_K", "P02_Pa"),
        ("3  compressor exit",    "T03_K", "P03_Pa"),
        ("4  turbine inlet",      "T04_K", "P04_Pa"),
        ("5  turbine exit",       "T05_K", "P05_Pa"),
    ]
    print("\nSTATION TABLE\n" + "=" * 52)
    print(f"{'station':<22}{'T0 [K]':>12}{'P0 [kPa]':>16}")
    lines = ["station,T0_K,P0_kPa"]
    for label, tk, pk in stations:
        print(f"{label:<22}{state[tk]:>12.1f}{state[pk]/1000:>16.1f}")
        lines.append(f"{label.strip()},{state[tk]:.2f},{state[pk]/1000:.3f}")
    with open(os.path.join(OUT, "station_table.csv"), "w") as f:
        f.write("\n".join(lines) + "\n")

    # ---- headline numbers ----------------------------------------------
    print("\nHEADLINE\n" + "=" * 52)
    head = [
        ("thrust target",        "F_target_N",   "N"),
        ("thrust sizing closure",      "F_gross_N",    "N"),
        ("air mass flow",        "mdot_kg_s",    "kg/s"),
        ("fuel flow",            "mdot_fuel_kg_s", "kg/s"),
        ("spool speed",          "N_rpm",        "rpm"),
        ("impeller diameter",    "D2_m",         "m"),
        ("impeller tip speed",   "U2_m_s",       "m/s"),
        ("turbine tip diameter", "D_turb_tip_m", "m"),
        ("turbine blade height", "h_blade_m",    "m"),
        ("NGV throat area",      "A_throat_ngv_m2", "m2"),
        ("nozzle exit diameter", "D8_m",         "m"),
        ("nozzle choked",        "nozzle_choked_flag", "0/1"),
        ("engine outer diameter","D_casing_out_m", "m"),
        ("engine length",        "L_engine_m",   "m"),
        ("dry mass",             "m_engine_kg",  "kg"),
    ]
    for label, key, unit in head:
        if key in state:
            print(f"{label:<24}{fmt(state[key]):>14}  {unit}")

    # ---- closure check --------------------------------------------------
    err = abs(state["F_gross_N"] - state["F_target_N"]) / state["F_target_N"]
    print("\nThrust closure checks internal consistency; mass flow is sized from the target.")
    print(f"\nthrust closure: {err*100:.3f}% "
          f"({'OK' if err < 0.01 else 'CHECK -- cycle and nozzle disagree'})")

    # ---- limits ---------------------------------------------------------
    print("\nSAFETY LIMITS (config/limits.yaml)\n" + "=" * 72)
    rows = check_limits(state, limits)
    n_bad = 0
    for label, key, v, op, lim, ok in rows:
        flag = "ok  " if ok else "FAIL"
        if not ok:
            n_bad += 1
        print(f"{flag}  {label:<34}{fmt(v):>12} {op} {fmt(lim):>12}")
    print("=" * 72)
    print(f"{len(rows)-n_bad}/{len(rows)} limits satisfied")

    # ---- CAD dimension table -------------------------------------------
    cad_map = registry.load_yaml("cad_map.yaml")
    cad = {}
    for cad_name, var in cad_map.items():
        if var not in state:
            raise ValueError(f"CAD variable missing: {var}")
        cad[cad_name] = round(state[var] * 1000.0, 4)   # mm for CAD
    with open(os.path.join(OUT, "cad_dims.json"), "w") as f:
        json.dump(cad, f, indent=2)
    with open(os.path.join(OUT, "cad_dims.csv"), "w") as f:
        f.write("parameter,value_mm\n")
        for k, v in cad.items():
            f.write(f"{k},{v}\n")
    print(f"\nwrote out/station_table.csv, out/cad_dims.json, out/cad_dims.csv "
          f"({len(cad)} CAD parameters)")

    # ---- full state dump ------------------------------------------------
    with open(os.path.join(OUT, "state.json"), "w") as f:
        json.dump({k: state[k] for k in sorted(state)}, f, indent=2)

    from core.readiness import blockers, design_fingerprint
    pending = blockers(HERE)
    report = {
        'release_status': 'PRELIMINARY - NOT FOR MANUFACTURE',
        'design_fingerprint': design_fingerprint(HERE),
        'failed_limits': [dict(label=label, variable=k, value=v, operator=op, limit=lim)
                          for label,k,v,op,lim,ok in rows if not ok],
        'evidence_blockers': pending,
        'critical_crossed_during_startup': bool(state['critical_crossed_flag']),
        'hole_counts': {k:v for k,v in state.items() if k.startswith(('n_holes','n_film','n_vaporizers'))},
        'cad_note': 'Liner cold dimensions at 293 K from prescribed uniform metal temperature; other component thermal fits unresolved.',
    }
    with open(os.path.join(OUT,'readiness.json'),'w') as f:
        json.dump(report,f,indent=2,allow_nan=False)
    print('\nPRELIMINARY - NOT FOR MANUFACTURE')
    print(f'{len(pending)} evidence blockers; critical crossed on startup: {bool(state["critical_crossed_flag"])}')
    if args.release_check:
        return 1 if n_bad or pending else 0
    return 0 if args.report_only else (1 if n_bad else 0)


if __name__ == "__main__":
    try:
        sys.exit(main() or 0)
    except BrokenPipeError:
        # piping into head/less closes stdout early; not an error
        os._exit(0)
