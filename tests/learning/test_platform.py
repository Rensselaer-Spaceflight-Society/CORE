"""Learning records, recovery, review safety, and real CLI/bundle journeys."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

REPO = Path(__file__).resolve().parents[2]
PLATFORM = REPO / "workspaces" / "python" / "interactive"
sys.path.insert(0, str(PLATFORM))
from learning_model import (Lesson, Question, Step, calculate, make_answer, parse_value,
                            validate_lesson)
from learning_store import (Session, export_session, read_json, recover, safe_child,
                            validate_record)
from learning_ui import interview, open_visual
from make_bundle import build
from review import build_report, comparisons, record_review, scan, select_latest
from runtime import discover, main


@pytest.fixture
def lesson():
    return discover()["START1"][0]


@pytest.fixture
def answers():
    return read_json(PLATFORM / "examples" / "fictional-answers.json")


def cli(*args, cwd=REPO):
    return subprocess.run([sys.executable, str(PLATFORM / "launch.py"), *map(str, args)],
                          input="", capture_output=True, text=True, encoding="utf-8",
                          cwd=cwd, timeout=20)


def fill(session, entries):
    for step in session.lesson.steps:
        for q in step.questions:
            if q.id in entries:
                session.record(q, entries[q.id])


def test_complete_resume_edit_and_export(tmp_path, lesson, answers):
    session = Session.create(lesson, "P01", tmp_path / "drafts")
    assert session.data["status"] == "in_progress"
    session.record(lesson.steps[0].questions[0], answers["target"])
    resumed = Session.load(lesson, "P01", session.data["session_id"], tmp_path / "drafts")
    fill(resumed, answers)
    assert resumed.data["status"] == "ready_for_review"
    assert resumed.data["review_status"] == "unreviewed"
    assert resumed.data["computed"][0]["value"] == 13
    original_revision = resumed.data["revision"]
    price = lesson.steps[2].questions[0]
    resumed.record(price, dict(answers["price"], value=20))
    assert resumed.data["computed"][0]["value"] == 23
    assert resumed.data["computed"][0]["inputs"]["price"]["source"] == "Invented one-item quote"
    old = read_json(resumed.folder / "history" / f"{original_revision:08d}.json")
    assert old["answers"]["price"]["value"] == 10
    a = export_session(resumed, tmp_path / "exports")
    b = export_session(resumed, tmp_path / "exports")
    assert a != b and (a / "summary.md").exists()
    exported = read_json(a / "answers.json")
    assert exported["review_status"] == "unreviewed"
    assert str(tmp_path) not in json.dumps(exported)


@pytest.mark.parametrize("value", ["nan", "inf", "-inf", float("nan"), True, "3,5", "twelve", -1])
def test_reject_invalid_number(value):
    with pytest.raises(ValueError):
        parse_value(Question("x", "value", kind="number", minimum=0), value)


def test_other_types_and_units():
    assert parse_value(Question("x", "x", kind="integer"), "3") == 3
    with pytest.raises(ValueError):
        parse_value(Question("x", "x", kind="integer"), "3.5")
    assert parse_value(Question("x", "x", kind="boolean"), "no") is False
    assert parse_value(Question("x", "x", kind="choice", choices=("a", "b")), "b") == "b"
    with pytest.raises(ValueError):
        parse_value(Question("x", "x", kind="number", units="K"), "400 K")


def test_not_found_and_missing_evidence(tmp_path, lesson):
    session = Session.create(lesson, "P02", tmp_path)
    q = lesson.steps[1].questions[0]
    with pytest.raises(ValueError, match="source"):
        session.record(q, {"value": "a claim"})
    with pytest.raises(ValueError, match="search trail"):
        session.record(q, {"status": "not_found"})
    session.record(q, {"status": "not_found", "reason": "Searched datasheet rev 2, no output type."})
    assert session.data["answers"][q.id]["value"] is None
    assert session.data["status"] == "in_progress"


def test_missing_calculation_inputs_stay_missing(tmp_path, lesson, answers):
    session = Session.create(lesson, "P03", tmp_path)
    session.record(lesson.steps[2].questions[0], answers["price"])
    assert session.data["computed"][0]["status"] == "missing_inputs"
    assert session.data["computed"][0]["value"] is None


def test_two_students_and_sessions_do_not_collide(tmp_path, lesson):
    sessions = [Session.create(lesson, slot, tmp_path) for slot in ("P01", "P02", "P01")]
    assert len({s.folder for s in sessions}) == 3
    assert len(list(tmp_path.glob("*/*/*/answers.json"))) == 3


def test_concurrent_processes_get_separate_sessions(tmp_path):
    args = ("--lesson", "START1", "--slot", "P01", "--answers",
            PLATFORM / "examples" / "fictional-answers.json", "--data-dir", tmp_path)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: cli(*args), range(2)))
    assert all(r.returncode == 0 for r in results), [r.stderr for r in results]
    assert len(list(tmp_path.glob("*/*/*/answers.json"))) == 2


def test_stale_writer_cannot_overwrite(tmp_path, lesson, answers):
    a = Session.create(lesson, "P01", tmp_path)
    b = Session.load(lesson, "P01", a.data["session_id"], tmp_path)
    q = lesson.steps[0].questions[0]
    a.record(q, answers["target"])
    with pytest.raises(ValueError, match="Another window"):
        b.record(q, {"value": "stale entry"})
    assert read_json(a.folder / "answers.json")["answers"][q.id]["value"] == answers["target"]["value"]


def test_lock_failure_and_recovery(tmp_path, lesson):
    s = Session.create(lesson, "P01", tmp_path)
    (s.folder / ".write-lock").touch()
    with pytest.raises(ValueError, match="being saved elsewhere"):
        s.save()
    recovered = recover(lesson, "P01", s.data["session_id"], tmp_path)
    assert recovered.folder != s.folder
    assert (s.folder / ".write-lock").exists()


def test_corrupt_and_interrupted_save_recovers_latest_history(tmp_path, lesson, answers, monkeypatch):
    import learning_store
    s = Session.create(lesson, "P01", tmp_path)
    original = learning_store.os.replace
    def fail_current(source, destination):
        if Path(destination).name == "answers.json":
            raise PermissionError("simulated disk failure")
        original(source, destination)
    monkeypatch.setattr(learning_store.os, "replace", fail_current)
    with pytest.raises(PermissionError):
        s.record(lesson.steps[0].questions[0], answers["target"])
    monkeypatch.setattr(learning_store.os, "replace", original)
    (s.folder / "answers.json").write_text("broken", encoding="utf-8")
    recovered = recover(lesson, "P01", s.data["session_id"], tmp_path)
    assert recovered.data["answers"]["target"]["value"] == answers["target"]["value"]
    assert (s.folder / "answers.json").read_text() == "broken"


def test_lesson_change_requires_original_version(tmp_path, lesson):
    s = Session.create(lesson, "P01", tmp_path)
    with pytest.raises(ValueError, match="another lesson revision"):
        Session.load(replace(lesson, version="2"), "P01", s.data["session_id"], tmp_path)


def test_path_and_slot_validation(tmp_path, lesson):
    for slot in ("../../elsewhere", "Andy", "P01/../../x", "P1"):
        with pytest.raises(ValueError):
            Session.create(lesson, slot, tmp_path)
    with pytest.raises(ValueError):
        safe_child(tmp_path, "..", "escape")


def test_duplicate_keys_and_approval_forgery(tmp_path, lesson):
    file = tmp_path / "bad.json"
    file.write_text('{"x":1,"x":2}')
    with pytest.raises(ValueError, match="Duplicate"):
        read_json(file)
    s = Session.create(lesson, "P01", tmp_path / "drafts")
    s.data["review_status"] = "approved"
    with pytest.raises(ValueError, match="approval"):
        validate_record(s.data)


def test_review_escapes_html_and_never_executes_submissions(tmp_path, lesson, answers):
    s = Session.create(lesson, "P01", tmp_path / "drafts")
    malicious = '<script>alert("x")</script>\nUnicode: \u03c0 and quotes "yes"'
    fill(s, dict(answers, target={"value": malicious}))
    export = export_session(s, tmp_path / "exports")
    (export / "evil.py").write_text("raise RuntimeError('must never execute')")
    output = build_report(tmp_path / "exports", tmp_path / "report" / "index.html")
    content = output.read_text(encoding="utf-8")
    assert malicious not in content
    assert "&lt;script&gt;" in content
    assert "Full evidence JSON" in content
    review = record_review(export / "answers.json", "Structures lead", "follow_up", "Need conditions.")
    assert review.exists()
    assert read_json(export / "answers.json")["review_status"] == "unreviewed"


def test_report_handles_corrupt_export_and_duplicate_snapshots(tmp_path, lesson, answers):
    s = Session.create(lesson, "P01", tmp_path / "drafts")
    fill(s, answers)
    a = export_session(s, tmp_path / "exports")
    b = export_session(s, tmp_path / "exports")
    records, errors = scan(tmp_path / "exports")
    selected, notices = select_latest(records)
    assert len(selected) == 1 and notices and not errors
    (b / "answers.json").write_text("not JSON")
    output = build_report(tmp_path / "exports", tmp_path / "index.html")
    assert "1 unreadable" in output.read_text()
    assert (a / "answers.json").exists()


def test_comparison_keys_only_compare_explicit_same_quantity(tmp_path):
    q = Question("diameter", "Diameter", kind="number", units="mm", comparison_key="part-A.rev2.diameter")
    lesson = validate_lesson(Lesson("TEST", "1", "Test", "Lead", (Step("s", "s", "s", (q,)),)))
    records = []
    for slot, value in (("P01", 10), ("P02", 11)):
        s = Session.create(lesson, slot, tmp_path)
        s.record(q, dict(value=value, source="drawing", uncertainty="revision unclear"))
        records.append((s.data, s.folder / "answers.json"))
    assert "Different reports" in comparisons(records)[0]


def test_noninteractive_default_is_read_only(tmp_path):
    result = cli("--lesson", "START1", "--data-dir", tmp_path / "not created")
    assert result.returncode == 2 and "terminal" in result.stderr
    assert not (tmp_path / "not created").exists()
    assert cli("--list").returncode == 0
    assert cli("--lesson", "START1", "--preview").returncode == 0


def test_bad_batch_validates_before_creating_session(tmp_path):
    batch = tmp_path / "input.json"
    batch.write_text('{"price":{"value":"NaN"}}')
    result = cli("--lesson", "START1", "--slot", "P01", "--answers", batch,
                 "--data-dir", tmp_path / "drafts")
    assert result.returncode == 2
    assert not (tmp_path / "drafts").exists()


def test_interview_draft_survives_interrupt_and_resume(tmp_path, lesson, monkeypatch):
    s = Session.create(lesson, "P01", tmp_path)
    s.move(1)
    values = iter(["Unicode finding: \u03c0", "sourced"])
    def interrupted(prompt):
        try:
            return next(values)
        except StopIteration:
            raise KeyboardInterrupt()
    monkeypatch.setattr("builtins.input", interrupted)
    assert interview(s, PLATFORM / "lessons" / "orientation" / "start_here.py") == 0
    loaded = Session.load(lesson, "P01", s.data["session_id"], tmp_path)
    assert loaded.data["drafts"]["finding"]["value"] == "Unicode finding: \u03c0"
    assert "finding" not in loaded.data["answers"]
    # Keep two previous fields with Enter, then finish the source/limits fields.
    values = iter(["", "", "datasheet", "rev2", "", "not independently checked", "/quit"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(values))
    assert interview(loaded, PLATFORM / "lessons" / "orientation" / "start_here.py") == 0
    assert loaded.data["answers"]["finding"]["value"] == "Unicode finding: \u03c0"


def test_interview_navigation_skip_multiline_export(tmp_path, lesson, monkeypatch):
    s = Session.create(lesson, "P01", tmp_path / "drafts")
    values = iter(["/help", "/progress", "/text", "line one", 'line "two"', ".",
                   "/not-found", "Checked catalog rev2; output missing", "/skip", "/skip",
                   "Which part?", "Ask lead", "/back", "/next", "/edit target", "/next",
                   "/export", "/quit"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(values))
    assert interview(s, PLATFORM / "lessons" / "orientation" / "start_here.py", tmp_path / "exports") == 0
    assert s.data["answers"]["target"]["value"] == 'line one\nline "two"'
    assert s.data["status"] == "ready_for_review"
    assert len(list((tmp_path / "exports").glob("*/*/*/answers.json"))) == 1


def test_missing_browser_is_nonfatal(lesson, monkeypatch, capsys):
    monkeypatch.setattr("learning_ui.webbrowser.open", lambda uri: False)
    open_visual(PLATFORM / "lessons" / "orientation" / "start_here.py", lesson.steps[0])
    assert "did not open" in capsys.readouterr().out


def test_standalone_offline_bundle_in_path_with_spaces(tmp_path):
    bundle = build(tmp_path / "bundle.zip")
    with zipfile.ZipFile(bundle) as archive:
        assert not any(Path(x).name == "answers.json" or "__pycache__" in x for x in archive.namelist())
        archive.extractall(tmp_path / "student folder")
    root = tmp_path / "student folder" / "CORE-learning"
    lesson = root / "workspaces/python/interactive/lessons/orientation/start_here.py"
    fixture = root / "workspaces/python/interactive/examples/fictional-answers.json"
    result = subprocess.run([sys.executable, "-S", str(lesson), "--slot", "P00", "--answers",
                             str(fixture), "--export"], cwd=tmp_path, capture_output=True,
                            text=True, encoding="utf-8", timeout=20)
    assert result.returncode == 0, result.stderr
    assert len(list((root / "workspaces/submissions").glob("*/*/*/answers.json"))) == 1
    assert not (root / "config").exists()
