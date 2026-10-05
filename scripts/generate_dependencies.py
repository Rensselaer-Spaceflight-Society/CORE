"""Generate the exact module data-flow diagram; CI rejects stale documentation."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import run
from core import registry, solver


def _candidate_section():
    """Candidate module set (fixed-geometry rating) with the case seed, if the case file exists."""
    from core import cases, candidate
    case = cases.load_case('pd1-jm85')
    specs = run.load_all_modules('candidate')
    seeded = set(registry.load_seed()) | set(registry.load_limits()) | set(case.get('seed_overrides') or {})
    seeded |= {'cycle_imported_point_flag', 'compressor_fixed_wheel_flag', 'turbine_fixed_wheel_flag', 'ngv_fixed_flag',
               'nozzle_fixed_flag', 'assembly_mode_flag'}
    from core import assembly
    seeded |= {k for k in assembly.STACK_READS if not any(k in m.writes for m in specs)}
    seeded |= {'op_mdot_air_kg_s', 'op_mdot_comb_kg_s', 'op_mdot_fuel_kg_s', 'op_P02_Pa', 'op_T03_K', 'op_P03_Pa',
               'op_P031_Pa', 'op_P04_Pa', 'op_T05_K', 'op_P05_Pa', 'op_P07_Pa', 'op_w_comp_J_kg', 'op_w_turb_J_kg',
               'op_F_gross_N', 'A8_fixed_m2', 'nozzle_Cd_ratio', 'k_support_N_m', 'c_support_N_s_m'}
    plan = solver.build_plan(specs, seeded)
    edges = {(plan.producers[r].name, m.name) for m in specs for r in tuple(m.reads) + tuple(m.optional_reads)
             if r in plan.producers}
    lines = ['## Candidate module set (`module_set: candidate`, fixed-geometry rating)', '',
             'Includes optional (mode-selected) reads. M01 imports the matched operating point; M29 adds the explicit stack.',
             '', '```mermaid', 'flowchart TD']
    for m in sorted(specs, key=lambda m: m.name):
        lines.append(f'    {m.name}["{m.name}: {m.title}"]')
    for a, b in sorted(edges):
        lines.append(f'    {a} --> {b}')
    lines += ['```', '', '```text', plan.describe(), '```', '']
    return lines


def document():
    specs = run.load_all_modules()
    plan = solver.build_plan(specs, set(registry.load_seed()) | set(registry.load_limits()))
    lines = ['# Generated module dependencies', '',
             'Generated from `reads` and `writes`; arrows mean information flow, not gas flow.', '',
             'Regenerate with `python scripts/generate_dependencies.py`.', '', '```mermaid', 'flowchart TD']
    for m in sorted(specs, key=lambda m: m.name):
        lines.append(f'    {m.name}["{m.name}: {m.title}"]')
    edges = {(plan.producers[r].name, m.name) for m in specs for r in m.reads if r in plan.producers}
    for a,b in sorted(edges):
        lines.append(f'    {a} --> {b}')
    lines += ['```', '', '## Execution order', '', '```text', plan.describe(), '```', '',
              'Independent branches may be designed concurrently. No calibrated component-efficiency feedback currently exists.', '']
    lines += _candidate_section()
    return '\n'.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    path = ROOT/'docs/generated-dependencies.md'
    text = document()
    if args.check:
        if not path.exists() or path.read_text(encoding='utf-8') != text:
            raise SystemExit('Dependency diagram is stale: run python scripts/generate_dependencies.py')
    else:
        path.write_text(text, encoding='utf-8')
