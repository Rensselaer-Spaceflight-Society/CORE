"""Read exported JSON evidence without executing student code. Local HTML report."""

import argparse
from collections import defaultdict
import html
import json
import os
from pathlib import Path
from urllib.parse import quote
import uuid

from learning_store import (PROJECT_ROOT, atomic_write, digest, now, read_json,
                            safe_child, validate_record)


def scan(root):
    root = Path(root).resolve()
    records, errors = [], []
    if not root.is_dir():
        raise ValueError("Submission directory does not exist. Export a session first.")
    for path in sorted(root.glob("*/*/*/answers.json")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            errors.append((relative, "Skipped a link outside the submission directory."))
            continue
        try:
            data = validate_record(read_json(path))
            if (path.parent.parent.name != data["lesson"]["id"] or
                    path.parent.parent.parent.name != data["participant_slot"]):
                raise ValueError("Folder does not match slot/lesson metadata.")
            records.append((data, path))
        except (OSError, ValueError, RecursionError) as exc:
            errors.append((relative, str(exc)))
    return records, errors


def select_latest(records):
    groups = defaultdict(list)
    for data, path in records:
        groups[(data["participant_slot"], data["lesson"]["id"], data["session_id"])].append((data, path))
    latest, notices = [], []
    for key, group in groups.items():
        group.sort(key=lambda x: (x[0]["revision"], x[0]["updated_at"], x[1].as_posix()), reverse=True)
        max_revision = group[0][0]["revision"]
        current = [r for r in group if r[0]["revision"] == max_revision]
        distinct = {digest(data) for data, _ in current}
        if len(distinct) > 1:
            notices.append(f"Conflicting exports of session {key[2]} at revision {max_revision}; showing all.")
            latest.extend(current)
        else:
            latest.append(group[0])
        if len(group) > 1:
            notices.append(f"Session {key[2]} has {len(group)} exports; older/identical copies retained on disk.")
    return latest, notices


def comparisons(records):
    groups = defaultdict(list)
    for data, _ in records:
        for a in data["answers"].values():
            if not a["comparison_key"] or a["status"] != "answered":
                continue
            # No unit conversion or inferred semantic matching in the review layer.
            groups[(a["comparison_key"], a["units"])].append((data["participant_slot"], a))
    messages = []
    for (key, units), items in groups.items():
        if len(items) < 2:
            continue
        values = {json.dumps(a["value"], sort_keys=True) for _, a in items}
        label = "Different reports: check sources/conditions" if len(values) > 1 else "Repeated value: not independent verification"
        messages.append(f"{key} [{units or 'unitless'}] — {label}. " +
                        "; ".join(f"{slot}: {a['value']} ({a['basis']})" for slot, a in items))
    return messages


def record_review(path, role, outcome, note):
    path = Path(path).resolve()
    data = validate_record(read_json(path))
    if not role.strip() or not note.strip() or outcome not in ("follow_up", "source_checked", "candidate_recorded"):
        raise ValueError("Review needs a role, note and permitted outcome.")
    result = dict(schema_version=1, record_digest=digest(data), session_id=data["session_id"],
                  revision=data["revision"], reviewed_at=now(), reviewer_role=role.strip(),
                  outcome=outcome, note=note.strip(),
                  meaning="Human-entered review annotation; not authenticated approval or hardware release.")
    target = safe_child(path.parent, "reviews", uuid.uuid4().hex + ".json")
    atomic_write(target, result)
    return target


def review_annotations(path, data):
    notes = []
    folder = safe_child(path.parent, "reviews")
    for item in sorted(folder.glob("*.json")):
        if item.is_symlink() or not item.resolve().is_relative_to(path.parent.resolve()):
            continue
        try:
            note = read_json(item)
            if note.get("record_digest") != digest(data):
                notes.append("Review annotation refers to another snapshot; not applied.")
            else:
                notes.append(" | ".join(str(note.get(k, "")) for k in
                                        ("reviewed_at", "reviewer_role", "outcome", "note")))
        except (OSError, ValueError, AttributeError, RecursionError):
            notes.append("Unreadable review annotation; inspect the original file.")
    return notes


STYLE = """body{font:16px/1.55 system-ui,sans-serif;background:#f3f6f9;color:#192b3b;margin:0}
main{max-width:1100px;margin:auto;padding:32px}h1{font-size:32px;margin-bottom:4px}
.intro{max-width:850px;color:#425366}.card{background:white;padding:24px;border-radius:12px;
margin:24px 0;border:1px solid #d6e0e8}h2{margin-top:0}h3{font-size:17px}
.tag{display:inline-block;background:#e3edf6;padding:4px 10px;border-radius:5px}
dt{font-weight:650;margin-top:16px}dd{margin:4px 0 12px;white-space:pre-wrap;overflow-wrap:anywhere}
.muted{color:#556475}.alert{border-left:5px solid #ba730a;padding-left:16px}
li{overflow-wrap:anywhere}a{color:#075da5}details{margin:14px 0}summary{cursor:pointer}
pre{white-space:pre-wrap;overflow-wrap:anywhere}
@media(max-width:600px){main{padding:14px}.card{padding:16px}}"""


def build_report(root, output):
    records, errors = scan(root)
    current, notices = select_latest(records)
    output = Path(output).resolve()
    e = lambda value: html.escape(str(value), quote=True)
    parts = ["<!doctype html><html lang='en'><meta charset='utf-8'>",
             "<meta name='viewport' content='width=device-width, initial-scale=1'>",
             "<title>CORE learning review</title><style>" + STYLE + "</style><main>",
             "<h1>Research ready for a conversation</h1>",
             "<p class='intro'>Individual findings, their evidence and the next decisions. "
             "This report reads data only. It does not run student scripts or approve engineering.</p>",
             f"<p>{len(current)} current session records · {len(errors)} unreadable records · Generated {e(now())}</p>"]
    messages = notices + comparisons(current)
    if messages or errors:
        parts.append("<section class='card alert'><h2>Items to reconcile</h2><ul>")
        parts += ["<li>" + e(m) + "</li>" for m in messages]
        parts += ["<li>" + e(path + ": " + error) + "</li>" for path, error in errors]
        parts.append("</ul></section>")
    for data, path in current:
        lesson = data["lesson"]
        parts.extend(["<section class='card'>",
                      f"<h2>{e(data['participant_slot'])} · {e(lesson['id'])} — {e(lesson['title'])}</h2>",
                      f"<span class='tag'>{e(data['status'].replace('_', ' '))}</span>",
                      f"<p class='muted'>Reviewer role: {e(lesson['review_role'])}. Lesson {e(lesson['version'])}; "
                      f"record revision {data['revision']}. Engineering approval: not established.</p>"])
        for role, heading in (("decision", "Decisions / questions"), ("next_step", "Next steps"), ("finding", "Findings")):
            parts.append("<details><summary>Findings and supporting sources</summary><dl>" if role == "finding"
                         else "<h3>" + heading + "</h3><dl>")
            for q in lesson["question_specs"]:
                if q["role"] != role:
                    continue
                a = data["answers"].get(q["id"])
                parts.append("<dt>" + e(q["prompt"]) + "</dt>")
                if not a:
                    parts.append("<dd>Not recorded</dd>")
                    continue
                value = f"{a['value']} {a['units']}" if a["status"] == "answered" else a["status"]
                parts.append("<dd>" + e(value) + "</dd>")
                evidence = "\n".join(f"{k}: {a[k]}" for k in
                                     ("basis", "source", "source_revision", "assumptions", "uncertainty", "reason") if a[k])
                if evidence != "basis: student":
                    parts.append("<dd class='muted'>" + e(evidence) + "</dd>")
            parts.append("</dl>")
            if role == "finding":
                parts.append("</details>")
        if data["computed"]:
            parts.append("<details><summary>Calculated teaching results (not independently verified)</summary><dl>")
            for c in data["computed"]:
                parts.append("<dt>" + e(c.get("title", "Calculation")) + "</dt>")
                value = (f"{c.get('value')} {c.get('units', '')}" if c.get("status") == "computed"
                         else str(c.get("status", "unknown")).replace("_", " "))
                parts.append("<dd>" + e(value) + "\nMethod: " + e(c.get("method", "unknown")) +
                             "\nLimits: " + e(c.get("limitations", "unknown")) + "</dd>")
            parts.append("</dl></details>")
        for note in review_annotations(path, data):
            parts.append("<p class='alert'>Review note: " + e(note) + "</p>")
        try:
            relative = Path(os.path.relpath(path, output.parent)).as_posix()
            parts.append(f"<a href='{e(quote(relative, safe='/'))}'>Full evidence JSON</a>")
        except ValueError:
            parts.append("<p>Full evidence is in the selected submission directory (another drive).</p>")
        parts.append("</section>")
    parts.append("</main></html>")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(parts), encoding="utf-8")
    return output


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=PROJECT_ROOT / "workspaces" / "submissions")
    p.add_argument("--output", type=Path, default=PROJECT_ROOT / "out" / "learning-review" / "index.html")
    p.add_argument("--record", type=Path, help="Exact answers.json to annotate; must be under --root")
    p.add_argument("--role")
    p.add_argument("--outcome", choices=("follow_up", "source_checked", "candidate_recorded"))
    p.add_argument("--note")
    args = p.parse_args(argv)
    try:
        if args.record:
            if not args.record.resolve().is_relative_to(args.root.resolve()):
                raise ValueError("Review record must be within --root.")
            print(record_review(args.record, args.role or "", args.outcome, args.note or ""))
        print(build_report(args.root, args.output))
        return 0
    except (OSError, ValueError, RecursionError) as exc:
        print("Could not create review:", exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
