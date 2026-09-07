"""Make failed engineering limits visible in a passing software-CI run."""
import json
import os
from pathlib import Path

r = json.loads(Path('out/readiness.json').read_text())
lines = ['## CORE preliminary design report', '', '**NOT FOR MANUFACTURE**', '',
         'Software tests and design approval are separate. Current failed screening limits:', '']
for row in r['failed_limits']:
    lines.append(f"- {row['label']}: {row['value']:.5g} {row['operator']} {row['limit']:.5g} is not satisfied.")
lines += ['', f"Critical crossed during startup: **{r['critical_crossed_during_startup']}**", '',
          'Evidence blockers:', '']
lines += ['- '+b for b in r['evidence_blockers']]
lines += ['', 'Download the preliminary-report artifact for dimensions, counts, state and design fingerprint.', '']
text = '\n'.join(lines)
print(text)
if os.environ.get('GITHUB_STEP_SUMMARY'):
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f:
        f.write(text)
