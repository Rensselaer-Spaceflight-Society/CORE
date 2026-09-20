"""Public API v1: lesson authors import these classes and run_lesson."""

import argparse
import importlib.util
from pathlib import Path
import sys

from learning_model import (Calculation, Lesson, Question, Step, SLOT_RE,
                            questions, validate_lesson)
from learning_store import (PROJECT_ROOT, Session, export_session, read_json,
                            recover, safe_child, validate_record)
from learning_ui import interview, progress

HERE = Path(__file__).resolve().parent


def discover():
    """Import trusted, tracked lesson modules only; never imports submissions."""
    found = {}
    for source in sorted((HERE / "lessons").glob("*/*.py")):
        if source.name.startswith("_") or source.is_symlink():
            continue
        module_name = "_core_learning_" + source.parent.name + "_" + source.stem
        spec = importlib.util.spec_from_file_location(module_name, source)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        if not hasattr(module, "build_lesson"):
            continue
        lesson = validate_lesson(module.build_lesson())
        if lesson.id in found:
            raise ValueError("Duplicate lesson ID: " + lesson.id)
        found[lesson.id] = (lesson, source)
    return found


def sessions(root, slot, lesson=None):
    if not SLOT_RE.fullmatch(slot):
        raise ValueError("Use an anonymous slot such as P01.")
    folder = safe_child(root, slot)
    found = []
    for path in sorted(folder.glob("*/*/answers.json")):
        if path.is_symlink() or not path.resolve().is_relative_to(folder):
            continue
        if lesson and path.parent.parent.name != lesson.id:
            continue
        try:
            data = validate_record(read_json(path))
            if data["participant_slot"] != slot:
                raise ValueError("Slot mismatch.")
            found.append((data, path.parent))
        except (OSError, ValueError, RecursionError):
            print("Unreadable session", path.parent.name, "- originals kept; try --recover.")
    return sorted(found, key=lambda pair: pair[0]["updated_at"], reverse=True)


def parser():
    p = argparse.ArgumentParser(description="CORE guided research: learn, save, resume, submit.")
    p.add_argument("--list", action="store_true", help="List installed guided lessons; no writes")
    p.add_argument("--lesson", help="Lesson ID from --list")
    p.add_argument("--slot", help="Assigned anonymous participant slot, e.g. P01")
    p.add_argument("--list-sessions", action="store_true")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--resume", metavar="SESSION_ID")
    group.add_argument("--recover", metavar="SESSION_ID", help="Recover history into a NEW session")
    group.add_argument("--new", action="store_true", help="Explicitly start a separate session")
    p.add_argument("--preview", "--form", action="store_true", help="Print lesson/form; no writes")
    p.add_argument("--answers", type=Path, help="Explicit noninteractive JSON answer batch; validated")
    p.add_argument("--export", action="store_true", help="Explicitly export; does not upload")
    p.add_argument("--data-dir", type=Path, default=PROJECT_ROOT / "out" / "learning")
    p.add_argument("--export-dir", type=Path, default=PROJECT_ROOT / "workspaces" / "submissions")
    return p


def print_preview(lesson):
    print(lesson.id, "|", lesson.title, "|", lesson.version)
    print("Reviewer:", lesson.review_role, "|", lesson.minutes, "minutes")
    for step in lesson.steps:
        print("\n" + step.title + "\n" + step.teaching)
        for q in step.questions:
            print(f"  {q.id}: {q.prompt} ({q.kind}; units: {q.units or 'none'})")
            print("    Answer: ______________________________")
            if q.evidence:
                print("    Basis / source / revision / assumptions / uncertainty: ______________")
            print("    UNKNOWN or NOT FOUND + where you looked are welcome.")
    print("\nSources:")
    for source in lesson.sources:
        print(" ", source)
    print("Paper/doc answers can be returned to your lead. No files were written.")


def execute(args, fixed=None):
    catalog = {fixed[0].id: fixed} if fixed else discover()
    if args.list:
        for key, (lesson, source) in catalog.items():
            print(f"{key}: {lesson.title} | {source.relative_to(HERE).as_posix()}")
        return 0
    if args.list_sessions:
        if not args.slot:
            raise ValueError("--list-sessions needs --slot P01 (your assigned slot).")
        for data, _ in sessions(args.data_dir, args.slot):
            print(data["lesson"]["id"], data["session_id"], data["updated_at"], data["status"])
        return 0
    key = args.lesson or (fixed[0].id if fixed else None)
    if not key:
        if not sys.stdin.isatty():
            raise ValueError("No interactive terminal. Use --list, --preview --lesson ID, "
                             "or an explicit --answers file with --slot.")
        for code, (lesson, _) in catalog.items():
            print(code + " - " + lesson.title)
        key = input("Lesson code: ").strip()
    if key not in catalog:
        raise ValueError("Unknown guided lesson. Use --list. Older worksheets still run separately.")
    lesson, source = catalog[key]
    validate_lesson(lesson)
    if args.preview:
        print_preview(lesson)
        return 0
    if not args.answers and not args.export and not sys.stdin.isatty():
        raise ValueError("This lesson asks questions in a terminal. Use --preview for a read-only "
                         "form, or --answers FILE for an explicit noninteractive batch.")
    slot = args.slot
    if not slot:
        if not sys.stdin.isatty():
            raise ValueError("Noninteractive work needs --slot.")
        slot = input("Your assigned anonymous slot (e.g. P01): ").strip().upper()
    if not SLOT_RE.fullmatch(slot):
        raise ValueError("Use an assigned slot P01-P9999, not your name.")

    # Validate the whole batch before creating/modifying a session.
    entries = None
    if args.answers:
        from learning_model import make_answer
        from learning_store import now
        entries = read_json(args.answers)
        by_id = {q.id: q for q in questions(lesson)}
        if not isinstance(entries, dict) or not set(entries) <= set(by_id):
            raise ValueError("Answer batch must be an object keyed only by this lesson's question IDs.")
        for qid, entry in entries.items():
            make_answer(by_id[qid], entry, now())

    resume_id = args.resume
    if not resume_id and not args.recover and not args.new and entries is None and not args.export:
        previous = sessions(args.data_dir, slot, lesson)
        if previous:
            print("Saved sessions:")
            for index, (data, _) in enumerate(previous, 1):
                print(index, data["session_id"], data["updated_at"], data["status"])
            choice = input("Resume number, or n for a new session: ").strip().lower()
            if choice != "n":
                try:
                    number = int(choice)
                    if number < 1:
                        raise ValueError()
                    resume_id = previous[number - 1][0]["session_id"]
                except (ValueError, IndexError):
                    raise ValueError("Choose a displayed number or n. Existing sessions are unchanged.") from None
    if args.recover:
        session = recover(lesson, slot, args.recover, args.data_dir)
    elif resume_id:
        session = Session.load(lesson, slot, resume_id, args.data_dir)
    else:
        session = Session.create(lesson, slot, args.data_dir)
    if entries is not None:
        for q in questions(lesson):
            if q.id in entries:
                session.record(q, entries[q.id])
        pending = [i for i, q in enumerate(questions(lesson)) if q.id not in session.data["answers"]]
        session.move(pending[0] if pending else len(questions(lesson)))
        progress(session)
    if args.export:
        print("Exported:", export_session(session, args.export_dir))
        print("Review the files for private information before sharing. Nothing was uploaded.")
    if entries is not None or args.export:
        print("Session:", session.data["session_id"])
        return 0
    return interview(session, source, args.export_dir)


def main(argv=None, fixed=None):
    try:
        return execute(parser().parse_args(argv), fixed=fixed)
    except (OSError, ValueError, RecursionError) as exc:
        print("Could not finish:", exc, file=sys.stderr)
        print("Existing records were kept. Check the path/access or use --recover for corrupt "
              "sessions. Do not delete your work.", file=sys.stderr)
        return 2
    except (EOFError, KeyboardInterrupt):
        print("\nStopped; no further changes were made.")
        return 0


def run_lesson(lesson, source_file, argv=None):
    return main(argv, fixed=(validate_lesson(lesson), Path(source_file).resolve()))
