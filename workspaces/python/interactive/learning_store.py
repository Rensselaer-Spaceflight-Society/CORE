"""Atomic, versioned local records. Never writes engine configuration or Git."""

from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid

from learning_model import (SCHEMA_VERSION, SLOT_RE, Question, calculate,
                            completion, identifier, make_answer, questions)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MAX_RECORD_BYTES = 2_000_000


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def encode(data):
    return json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2) + "\n"


def digest(data):
    return hashlib.sha256(encode(data).encode("utf-8")).hexdigest()


def safe_child(root, *parts):
    root = Path(root).resolve()
    path = root.joinpath(*parts).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError(f"Path must stay inside the selected output folder: {root!s} -> {path!s}")
    return path


def read_json(path):
    path = Path(path)
    if path.stat().st_size > MAX_RECORD_BYTES:
        raise ValueError("Record is too large (limit: 2 MB).")
    def bad_constant(value):
        raise ValueError("Non-finite JSON number: " + value)
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key: " + key)
            result[key] = value
        return result
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=bad_constant,
                      object_pairs_hook=unique_pairs)


def atomic_write(path, data):
    path = Path(path)
    text = encode(data)
    if len(text.encode("utf-8")) > MAX_RECORD_BYTES:
        raise ValueError("Record exceeds 2 MB. Link large artifacts instead.")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


@contextmanager
def write_lock(folder):
    path = safe_child(folder, ".write-lock")
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError("This session is being saved elsewhere. Close its other window. "
                         "If a crash left a lock, use --recover to copy the last history "
                         "snapshot into a NEW session; do not overwrite this one.") from None
    os.close(descriptor)
    try:
        yield
    finally:
        path.unlink()


def revision():
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT,
                                capture_output=True, text=True, timeout=3, check=True)
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        source = PROJECT_ROOT / "SOURCE-REVISION.txt"
        return source.read_text(encoding="utf-8").strip() if source.exists() else "unknown"


def lesson_record(lesson):
    data = dict(id=lesson.id, version=lesson.version, title=lesson.title,
                review_role=lesson.review_role, sources=list(lesson.sources),
                question_specs=[asdict(q) for q in questions(lesson)])
    data["fingerprint"] = digest(dict(data, steps=[asdict(s) for s in lesson.steps],
                                    calculations=[dict(id=c.id, version=c.version,
                                                       method=c.method, inputs=c.inputs,
                                                       units=c.units, limitations=c.limitations)
                                                  for c in lesson.calculations]))
    return json.loads(encode(data))  # tuples become arrays, matching saved JSON exactly


def validate_record(data):
    """Validate data without importing any submitted lesson or running calculations."""
    try:
        if not isinstance(data, dict) or data["schema_version"] != SCHEMA_VERSION:
            raise ValueError("Unsupported record schema.")
        if not SLOT_RE.fullmatch(data["participant_slot"]):
            raise ValueError("Participant slot must look like P01 (no names).")
        if str(uuid.UUID(hex=data["session_id"])).replace("-", "") != data["session_id"]:
            raise ValueError("Invalid session ID.")
        lesson = data["lesson"]
        identifier(lesson["id"])
        if not all(isinstance(lesson[k], str) and lesson[k] for k in
                   ("version", "title", "review_role", "fingerprint")):
            raise ValueError("Invalid lesson metadata.")
        specs = [Question(**q) for q in lesson["question_specs"]]
        ids = {q.id for q in specs}
        if not ids or len(ids) != len(specs):
            raise ValueError("Duplicate or missing question IDs.")
        for q in specs:
            identifier(q.id)
        if not isinstance(data["answers"], dict) or not set(data["answers"]) <= ids:
            raise ValueError("Unknown question in answers.")
        for q in specs:
            if q.id in data["answers"]:
                ans = data["answers"][q.id]
                expected = make_answer(q, ans, ans["edited_at"])
                if ans != expected:
                    raise ValueError("Answer metadata does not match its question.")
        if not isinstance(data["drafts"], dict) or not set(data["drafts"]) <= ids:
            raise ValueError("Invalid draft questions.")
        if type(data["revision"]) is not int or data["revision"] < 1:
            raise ValueError("Invalid revision.")
        if type(data["current_step"]) is not int or not 0 <= data["current_step"] <= len(specs):
            raise ValueError("Invalid progress position.")
        for key in ("created_at", "updated_at"):
            if datetime.fromisoformat(data[key]).utcoffset() is None:
                raise ValueError("Timestamps need a timezone.")
        if data["review_status"] != "unreviewed":
            raise ValueError("Student records cannot assert review approval.")
        if data["status"] not in ("in_progress", "ready_for_review"):
            raise ValueError("Invalid completion status.")
        # Do not trust a student's claimed readiness; derive it from the typed records.
        ready = all(not q.required or data["answers"].get(q.id, {}).get("status")
                    in ("answered", "not_found") for q in specs)
        if (data["status"] == "ready_for_review") != ready:
            raise ValueError("Completion status disagrees with the answers.")
        if not isinstance(data["computed"], list):
            raise ValueError("Computed results must be a list.")
        for result in data["computed"]:
            if not isinstance(result, dict) or result.get("basis") != "computed":
                raise ValueError("Invalid computed result.")
        encode(data)  # also reject non-finite nested values
    except (KeyError, TypeError, AttributeError, OverflowError) as exc:
        raise ValueError("Malformed learning record.") from exc
    return data


class Session:
    def __init__(self, lesson, folder, data):
        self.lesson = lesson
        self.folder = Path(folder)
        self.data = data
        self.disk_revision = data["revision"]

    @classmethod
    def create(cls, lesson, slot, root=None):
        if not SLOT_RE.fullmatch(slot):
            raise ValueError("Use an assigned anonymous slot such as P01, not a name.")
        root = Path(root) if root is not None else PROJECT_ROOT / "out" / "learning"
        session_id = uuid.uuid4().hex
        folder = safe_child(root, slot, lesson.id, session_id)
        folder.mkdir(parents=True, exist_ok=False)
        data = dict(schema_version=SCHEMA_VERSION, session_id=session_id,
                    participant_slot=slot, lesson=lesson_record(lesson),
                    repository_commit=revision(), created_at=now(), updated_at=now(),
                    revision=0, current_step=0, answers={}, drafts={}, computed=[],
                    status="in_progress", review_status="unreviewed")
        session = cls(lesson, folder, data)
        session.save()
        return session

    @classmethod
    def load(cls, lesson, slot, session_id, root=None):
        if not SLOT_RE.fullmatch(slot):
            raise ValueError("Invalid participant slot.")
        identifier(session_id)
        root = Path(root) if root is not None else PROJECT_ROOT / "out" / "learning"
        folder = safe_child(root, slot, lesson.id, session_id)
        data = validate_record(read_json(safe_child(folder, "answers.json")))
        if data["participant_slot"] != slot or data["session_id"] != session_id:
            raise ValueError("Session identity does not match its folder.")
        if data["lesson"] != lesson_record(lesson):
            raise ValueError("This session belongs to another lesson revision. Keep it; "
                             "use its original bundle or start a new session.")
        return cls(lesson, folder, data)

    def save(self):
        with write_lock(self.folder):
            path = safe_child(self.folder, "answers.json")
            if path.exists():
                on_disk = validate_record(read_json(path))
                if on_disk["revision"] != self.disk_revision:
                    raise ValueError("Another window saved this session. Your last entry "
                                     "was NOT saved. Copy it, reopen the session, and retry.")
            elif self.disk_revision:
                raise ValueError("Current record is missing. Recover into a new session.")
            self.data["revision"] = self.disk_revision + 1
            self.data["updated_at"] = now()
            self.data["status"], _ = completion(self.lesson, self.data["answers"])
            self.data["computed"] = calculate(self.lesson, self.data["answers"])
            validate_record(self.data)
            history = safe_child(self.folder, "history", f"{self.data['revision']:08d}.json")
            if history.exists():
                raise ValueError("A recovery snapshot already exists for this revision. "
                                 "Use --recover; no previous data was overwritten.")
            atomic_write(history, self.data)
            atomic_write(path, self.data)
            self.disk_revision = self.data["revision"]

    def record(self, question, entry):
        answer = make_answer(question, entry, now())
        self.data["answers"][question.id] = answer
        self.data["drafts"].pop(question.id, None)
        self.save()

    def draft(self, question_id, entry):
        self.data["drafts"][question_id] = dict(entry)
        self.save()

    def move(self, index):
        self.data["current_step"] = index
        self.save()


def recover(lesson, slot, session_id, root=None):
    """Copy newest valid matching history into a fresh session; preserve broken data."""
    if not SLOT_RE.fullmatch(slot):
        raise ValueError("Invalid participant slot.")
    identifier(session_id)
    root = Path(root) if root is not None else PROJECT_ROOT / "out" / "learning"
    folder = safe_child(root, slot, lesson.id, session_id)
    for path in sorted(safe_child(folder, "history").glob("*.json"), reverse=True):
        if path.is_symlink():
            continue
        try:
            data = validate_record(read_json(safe_child(folder, "history", path.name)))
            if (data["lesson"] != lesson_record(lesson) or data["participant_slot"] != slot
                    or data["session_id"] != session_id):
                continue
        except (OSError, ValueError, RecursionError):
            continue
        new = Session.create(lesson, slot, root)
        for key in ("answers", "drafts", "current_step"):
            new.data[key] = data[key]
        new.data["recovered_from"] = dict(session_id=session_id, revision=data["revision"])
        new.save()
        return new
    raise ValueError("No valid matching history found. Original files were preserved.")


def summary_text(data):
    lines = [f"# {data['lesson']['id']}: {data['lesson']['title']}", "",
             f"Slot: {data['participant_slot']} | Session: {data['session_id']}",
             f"Lesson version: {data['lesson']['version']} | Record revision: {data['revision']}",
             f"Status: {data['status']} | Review: unreviewed", "",
             "Learning evidence only. Completion and a merged PR do not approve a design.", ""]
    for q in data["lesson"]["question_specs"]:
        a = data["answers"].get(q["id"])
        lines.extend([f"## {q['id']}: {q['prompt']}", ""])
        if not a:
            lines.append("Not recorded (a saved draft may be available locally).")
        else:
            lines.extend([f"Value: {a['value']} {a['units']}" if a['status'] == 'answered'
                          else f"Status: {a['status']}", f"Basis: {a['basis']}"])
            for key in ("source", "source_revision", "assumptions", "uncertainty", "reason"):
                if a[key]:
                    lines.append(f"{key}: {a[key]}")
        lines.append("")
    lines.extend(["## Computed (not independently verified)", ""])
    for c in data["computed"]:
        lines.extend([f"{c['title']}: {c['status']} | {c['value']} {c['units']}",
                      f"Method: {c['method']} ({c['method_version']})",
                      f"Limits: {c['limitations']}", ""])
    return "\n".join(lines) + "\n"


def export_session(session, root=None):
    root = Path(root) if root is not None else PROJECT_ROOT / "workspaces" / "submissions"
    data = validate_record(read_json(safe_child(session.folder, "answers.json")))
    export_id = f"{data['session_id']}-r{data['revision']}-{uuid.uuid4().hex[:8]}"
    folder = safe_child(root, data["participant_slot"], data["lesson"]["id"], export_id)
    folder.mkdir(parents=True, exist_ok=False)
    # Export only completed answer records, never unfinished/private drafts.
    data["drafts"] = {}
    atomic_write(safe_child(folder, "answers.json"), data)
    safe_child(folder, "summary.md").write_text(summary_text(data), encoding="utf-8")
    return folder
