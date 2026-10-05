"""Named engine cases: loading, design identity, seed composition and run folders.

A case file (config/cases/<id>.yaml) names a mode, its component records and the
settings that define the design. Three modes keep sizing screens and ratings apart:

    thrust_sizing           legacy baseline: airflow sized from a thrust target (M01 mode 0)
    prescribed_flow_screen  airflow, PR and TIT prescribed; purchased wheel held fixed;
                            thrust is an output (M01 prescribed-flow flag) - a design screen
    fixed_geometry_rating   operating point SOLVED by core/engine_match.py for fixed
                            purchased/designed geometry and imported into the pipeline
                            (M01 imported-point flag) - a rating, not a sizing

The design fingerprint covers every file that can change a result (case file,
seed/limits/registry, every file under data/ - component, map, budget, systems and
interface records - and the calculation source). Run timestamps are kept out of it and written separately.
"""
from __future__ import annotations

import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml

from core.records import ROOT, load_record, fingerprint, RecordError

CASES_DIR = ROOT / 'config' / 'cases'
MODES = ('thrust_sizing', 'prescribed_flow_screen', 'fixed_geometry_rating')
CODE_GLOBS = ('core/*.py', 'modules/*.py')
DATA_GLOBS = ('data/**/*',)   # all record formats affect identity, not only YAML/CSV
CODE_FILES = ('run.py', 'run_case.py', 'requirements.txt')
CONFIG_FILES = ('config/limits.yaml', 'config/variables.yaml', 'config/initial_guess.yaml', 'config/cad_map.yaml')


class CaseError(Exception):
    pass


def list_cases():
    return sorted(p.stem for p in CASES_DIR.glob('*.yaml'))


def load_case(case_id):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', case_id):
        raise CaseError('case id must be a simple name, not a path')
    path = CASES_DIR / f'{case_id}.yaml'
    if not path.is_file():
        raise CaseError(f'unknown case {case_id!r}; available: {list_cases()}')
    with open(path, encoding='utf-8') as f:
        case = yaml.safe_load(f)
    if not isinstance(case, dict) or case.get('schema_version') != 1:
        raise CaseError(f'{path}: schema_version 1 mapping required')
    if case.get('case_id') != case_id:
        raise CaseError(f'{path}: case_id {case.get("case_id")!r} does not match file name')
    if case.get('mode') not in MODES:
        raise CaseError(f'{path}: mode must be one of {MODES}')
    if not (ROOT / case.get('seed_base', '')).is_file():
        raise CaseError(f'{path}: seed_base file missing')
    for role, rel in (case.get('components') or {}).items():
        if not (ROOT / rel).is_file():
            raise CaseError(f'{path}: component {role} file {rel} missing')
    for k, v in (case.get('seed_overrides') or {}).items():
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise CaseError(f'{path}: seed override {k} must be a finite number')
    case['_path'] = path
    return case


def case_records(case):
    recs = {}
    seen = {}
    for role, rel in (case.get('components') or {}).items():
        r = load_record(rel)
        if r.id in seen:
            raise RecordError(f'component id {r.id!r} used for both {seen[r.id]} and {role}')
        seen[r.id] = role
        recs[role] = r
    return recs


def design_files(case, recs=None):
    recs = recs if recs is not None else case_records(case)
    files = [case['_path'], ROOT / case['seed_base']]
    files += [ROOT / c for c in CONFIG_FILES]
    for r in recs.values():
        files.append(r.path)
        if r.data.get('data_file'):
            files.append(ROOT / r.data['data_file'])
    for g in DATA_GLOBS + CODE_GLOBS:
        files += sorted(p for p in ROOT.glob(g) if p.is_file())
    files += [ROOT / c for c in CODE_FILES if (ROOT / c).is_file()]
    return files


def case_fingerprint(case, recs=None, extra=None):
    return fingerprint(design_files(case, recs), extra=extra)


def compose_seed(case, extra=None):
    """Seed = base seed file + case overrides + (mode-specific) extra seeds.

    Every key that the case adds or changes is returned in `provenance` so the
    manifest shows which numbers came from where. Unknown keys are rejected later
    by the registry check in run_case.py.
    """
    from core import registry
    base = registry._coerce_numbers(yaml.safe_load(open(ROOT / case['seed_base'], encoding='utf-8')) or {},
                                    case['seed_base'])
    seed = dict(base)
    prov = {k: 'seed_base' for k in base}
    for k, v in (case.get('seed_overrides') or {}).items():
        seed[k] = float(v)
        prov[k] = 'case seed_overrides'
    for k, (v, src) in (extra or {}).items():
        if isinstance(v, bool):
            v = 1.0 if v else 0.0
        if not isinstance(v, (int, float)) or not math.isfinite(v):
            raise CaseError(f'derived seed {k} is not a finite number ({v!r}) from {src}')
        seed[k] = float(v)
        prov[k] = src
    return seed, prov


# ---------------------------------------------------------------------------- run folders
def git_identity():
    try:
        rev = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, timeout=20).stdout.strip()
        branch = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=ROOT, capture_output=True,
                                text=True, timeout=20).stdout.strip()
        dirty = bool(subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT, capture_output=True, text=True,
                                    timeout=30).stdout.strip())
        return dict(revision=rev, branch=branch, working_tree_dirty=dirty)
    except Exception as e:  # git missing is not a design failure
        return dict(revision=None, branch=None, working_tree_dirty=None, error=str(e))


def run_metadata():
    import numpy, scipy
    return dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), python=platform.python_version(),
                platform=platform.platform(), numpy=numpy.__version__, scipy=scipy.__version__,
                pyyaml=yaml.__version__, argv=sys.argv, git=git_identity())


class RunFolder:
    """out/<case>/<fingerprint[:12]>/ written via a staging folder.

    On success the staging folder replaces the final folder and out/<case>/LATEST.json
    points to it. On failure a FAILED.json is written in the staging folder (kept for
    diagnosis) and LATEST.json is marked stale, so an older successful run can never
    be mistaken for the current design.
    """

    def __init__(self, case_id, fp, out_root=None):
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', case_id) or not re.fullmatch(r'[0-9a-f]{64}', fp):
            raise CaseError('invalid case id or fingerprint for run directory')
        self.case_id, self.fp = case_id, fp
        self.root = (Path(out_root) if out_root else ROOT / 'out').resolve()
        self.case_dir = self.root / case_id
        self.final = self.case_dir / fp[:12]
        self.stage = self.case_dir / f'.staging-{fp[:12]}-{os.getpid()}'
        for target in (self.case_dir, self.stage, self.final):
            if not target.resolve().is_relative_to(self.root) or target.resolve() == self.root:
                raise CaseError(f'run path escapes output root: {target}')
        if self.stage.exists():
            shutil.rmtree(self.stage)
        self.stage.mkdir(parents=True)

    def path(self, *parts):
        p = self.stage.joinpath(*parts)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def write_json(self, name, obj):
        with open(self.path(name), 'w', encoding='utf-8') as f:
            json.dump(obj, f, indent=2, allow_nan=False, default=_json_default)

    def write_text(self, name, text):
        with open(self.path(name), 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)

    def commit(self):
        if self.final.exists():
            shutil.rmtree(self.final)
        # Windows/OneDrive can briefly hold handles on new files: retry the rename, then copy as a fallback.
        for attempt in range(20):
            try:
                self.stage.rename(self.final)
                break
            except PermissionError:
                time.sleep(1.0 + 0.5 * attempt)
        else:
            shutil.copytree(self.stage, self.final)
            shutil.rmtree(self.stage, ignore_errors=True)
        latest = dict(case_id=self.case_id, fingerprint=self.fp, run_dir=str(self.final.relative_to(self.root)),
                      status='success', utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
        with open(self.case_dir / 'LATEST.json', 'w', encoding='utf-8') as f:
            json.dump(latest, f, indent=2)
        return self.final

    def fail(self, err):
        with open(self.stage / 'FAILED.json', 'w', encoding='utf-8') as f:
            json.dump(dict(case_id=self.case_id, fingerprint=self.fp, error=str(err)), f, indent=2)
        latest_path = self.case_dir / 'LATEST.json'
        prev = None
        if latest_path.is_file():
            try:
                prev = json.loads(latest_path.read_text(encoding='utf-8'))
            except Exception:
                prev = None
        with open(latest_path, 'w', encoding='utf-8') as f:
            json.dump(dict(case_id=self.case_id, status='failed', failed_fingerprint=self.fp,
                           failed_stage_dir=str(self.stage.relative_to(self.root)), error=str(err),
                           previous_success=prev, previous_success_is_current=False), f, indent=2)


def _json_default(o):
    import numpy as np
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return o.as_posix()
    raise TypeError(f'not JSON serialisable: {type(o).__name__}')


def clean_floats(obj):
    """Replace NaN/inf by None so JSON stays strict (NaN means 'not defined here')."""
    import numpy as np
    if isinstance(obj, dict):
        return {k: clean_floats(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean_floats(v) for v in obj]
    if isinstance(obj, (float, np.floating)):
        return float(obj) if math.isfinite(obj) else None
    return obj
