"""Evidence checklist, separate from numerical screening limits.

This checks completeness, not the authenticity or technical adequacy of review.
Approval remains a named human responsibility in the design-review PR.
"""
import hashlib
from pathlib import Path
import yaml

REQUIRED = (
    'cycle_and_maps', 'combustor_pressure_and_stability', 'thermal_and_pattern_factor',
    'liner_material_and_buckling', 'rotor_strength_and_life', 'rotordynamics_and_balance',
    'bearings_lubrication_and_thrust', 'fuel_controls_and_shutdown',
    'containment_and_test_site', 'drawings_tolerances_and_processes',
)


def design_fingerprint(root):
    root = Path(root)
    paths = [p for folder in ('core','modules','config','scripts') for p in (root/folder).rglob('*')
             if p.suffix in ('.py','.yaml') and p.name != 'readiness.yaml']
    paths += [root/name for name in ('run.py','V22_CombustionChamberDesign.py',
              'RPM_Sweep_OffDesign.py','requirements.txt') if (root/name).is_file()]
    paths = sorted(paths)
    h = hashlib.sha256()
    for p in paths:
        h.update(p.relative_to(root).as_posix().encode())
        h.update(p.read_bytes().replace(b'\r\n',b'\n'))
    return h.hexdigest()


def blockers(root):
    root = Path(root).resolve()
    document = yaml.safe_load((root/'config/readiness.yaml').read_text()) or {}
    problems = []
    if document.get('design_fingerprint') != design_fingerprint(root):
        problems.append('Evidence does not cover the current design/code fingerprint')
    entries = document.get('evidence',{}) or {}
    for name in REQUIRED:
        e = entries.get(name,{})
        if e.get('status') != 'reviewed' or not e.get('reviewer') or not e.get('review_date'):
            problems.append(name+': review pending')
            continue
        artifact = (root/(e.get('artifact') or '')).resolve()
        if not artifact.is_relative_to(root) or not artifact.is_file():
            problems.append(name+': missing in-repository evidence artifact')
        elif hashlib.sha256(artifact.read_bytes()).hexdigest() != e.get('sha256'):
            problems.append(name+': evidence checksum missing or stale')
    return problems
