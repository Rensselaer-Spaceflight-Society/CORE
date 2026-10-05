"""R10 probe: run scripts/make_design_snapshot.main on a COPY of a run folder in a temp root.

Run from the repository root. Never touches out/ or docs/ of the repository.
"""
import importlib.util, json, shutil, sys, tempfile
from pathlib import Path
repo = Path('.').resolve()
sys.path.insert(0, str(repo))
from core import cases as C
spec = importlib.util.spec_from_file_location('snap', repo / 'scripts/make_design_snapshot.py')
snap = importlib.util.module_from_spec(spec); spec.loader.exec_module(snap)
case = 'pd1-jm85'
run = Path(json.loads((repo / 'out' / case / 'LATEST.json').read_text())['run_dir'].replace('\\', '/')).name
k = C.load_case(case)

def fresh_root():
    t = Path(tempfile.mkdtemp(prefix='snapprobe_'))
    src = repo / 'out' / case / run
    dst = t / 'out' / case / run
    shutil.copytree(src, dst)
    man = json.loads((dst / 'manifest.json').read_text(encoding='utf-8'))
    man['design_fingerprint'] = C.case_fingerprint(k, C.case_records(k), extra=man.get('run_options'))  # pretend current
    (dst / 'manifest.json').write_text(json.dumps(man), encoding='utf-8')
    (t / 'out' / case / 'LATEST.json').write_text(json.dumps(dict(case_id=case, fingerprint=man['design_fingerprint'],
                                                                  run_dir=f'{case}/{run}', status='success')))
    (t / 'docs/design/results').mkdir(parents=True)
    return t, dst

def attempt(label, mutate=None):
    t, dst = fresh_root()
    if mutate:
        mutate(dst)
    snap.ROOT = t
    try:
        snap.main([case])
        out = t / 'docs/design/results' / case
        res = f'ACCEPTED (SUMMARY.md {"present" if (out / "SUMMARY.md").exists() else "MISSING"}, {sum(1 for _ in out.rglob("*") if _.is_file())} files)'
    except SystemExit as e:
        res = f'REJECTED: {e}'
    shutil.rmtree(t, ignore_errors=True)
    print(f'{label:58s} -> {res}')
    return res

r1 = attempt('intact copy (manifest excluded from its own hash check)')
r2 = attempt('tampered station_table.csv', lambda d: (d / 'station_table.csv').write_text((d / 'station_table.csv').read_text() + 'x\n'))
r3 = attempt('tampered manifest generated_files hash (candidate_checks)', lambda d: (lambda m: (m['generated_files'].__setitem__('candidate_checks.json', '0' * 64), (d / 'manifest.json').write_text(json.dumps(m))))(json.loads((d / 'manifest.json').read_text())))
r4 = attempt('listed output deleted (robustness/robustness.json)', lambda d: (d / 'robustness/robustness.json').unlink())
r5 = attempt('stale run (fingerprint differs)', lambda d: (lambda m: (m.__setitem__('design_fingerprint', 'f' * 64), (d / 'manifest.json').write_text(json.dumps(m))))(json.loads((d / 'manifest.json').read_text())))
# r4 was ACCEPTED before the verification fix (a listed output could vanish silently); it must be rejected now
ok = (r1.startswith('ACCEPTED') and r2.startswith('REJECTED') and r3.startswith('REJECTED')
      and r4.startswith('REJECTED') and r5.startswith('REJECTED'))
print('missing-listed-output rejected:', r4.startswith('REJECTED'))
sys.exit(0 if ok else 1)
