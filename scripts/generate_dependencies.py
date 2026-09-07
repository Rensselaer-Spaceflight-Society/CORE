"""Generate the exact module data-flow diagram; CI rejects stale documentation."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import run
from core import registry, solver


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
