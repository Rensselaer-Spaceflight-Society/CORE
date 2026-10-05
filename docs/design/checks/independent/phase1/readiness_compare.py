"""Compare the committed (HEAD) and working-tree legacy readiness fingerprint/blockers.

Run from the repository root: python <this file> <path-to-readiness_head.py>
Read-only: computes both fingerprints and both blocker lists; writes nothing.
"""
import importlib.util, sys
from pathlib import Path
root = Path('.').resolve()
spec = importlib.util.spec_from_file_location('readiness_head', sys.argv[1])
old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
sys.path.insert(0, str(root))
from core import readiness as new
fo, fn = old.design_fingerprint(root), new.design_fingerprint(root)
bo, bn = old.blockers(root), new.blockers(root)
import yaml
doc = yaml.safe_load((root / 'config/readiness.yaml').read_text())
reviewed = [k for k, e in (doc.get('evidence') or {}).items() if (e or {}).get('status') == 'reviewed']
print('stored design_fingerprint:', doc.get('design_fingerprint'))
print('reviewed evidence entries:', reviewed)
print('HEAD fingerprint   :', fo[:16], '| new fingerprint:', fn[:16], '| differ:', fo != fn)
print('blockers identical :', bo == bn, '| count', len(bo), len(bn))
# what does the new scope add?
paths_old = set()
for folder in ('core', 'modules', 'config', 'scripts'):
    paths_old |= {p for p in (root / folder).rglob('*') if p.suffix in ('.py', '.yaml') and p.name != 'readiness.yaml'}
added = sorted(p.relative_to(root).as_posix() for p in (root / 'data').rglob('*') if p.is_file())
print('newly covered files:', len(added) + 1, '(data/** +', 'run_case.py)')
# would a reviewed record keyed to the OLD fingerprint survive under the new function? (simulate on a copy of the dict)
sim = dict(doc, design_fingerprint=fo)
print('simulated: doc keyed to HEAD-function fingerprint -> new function flags mismatch:', sim['design_fingerprint'] != fn)
sys.exit(0 if bo == bn and not reviewed else 1)
