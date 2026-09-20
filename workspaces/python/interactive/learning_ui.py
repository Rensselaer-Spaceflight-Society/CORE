"""Small terminal interview. A complete answer and every draft field are saved."""

import textwrap
import webbrowser

from learning_model import BASES, completion, parse_value, questions
from learning_store import export_session, safe_child

HELP = """Commands (available at any question):
  /help             show this help
  /back             previous question
  /edit QUESTION_ID jump to a question; existing answer stays until replacement
  /next             leave the current answer/draft unchanged and move on
  /skip             record UNKNOWN (not yet researched)
  /not-found        record a search trail for information you could not find
  /progress         show recorded findings and missing evidence
  /visual           open this step's optional local diagram
  /text             enter several lines; finish with a single . on its own line
  /save             save current progress locally
  /export           explicitly create a review bundle (no upload or commit)
  /quit             leave; accepted answers and draft fields are already saved
At a metadata field, Enter keeps its existing value. No design values are changed.
"""


class Command(Exception):
    pass


def tell(text):
    for paragraph in text.split("\n"):
        print(textwrap.fill(paragraph, width=86) if paragraph else "")


def ask(prompt, partial=None):
    value = input(prompt).strip()
    if value == "/text":
        print("Enter lines; a line containing only . finishes. /commands here are literal text.")
        lines = []
        while True:
            line = input("... ")
            if line == ".":
                break
            lines.append(line)
            if partial:
                partial("\n".join(lines))
        return "\n".join(lines)
    if value.startswith("/"):
        raise Command(value)
    return value


def progress(session):
    status, missing = completion(session.lesson, session.data["answers"])
    print("\n" + status.replace("_", " ").upper() + " | Engineering review: unreviewed")
    for q in questions(session.lesson):
        a = session.data["answers"].get(q.id)
        state = a["status"] if a else "not recorded"
        if q.id in session.data["drafts"]:
            state += " (draft saved)"
        print(f"  {q.id}: {state}")
    print("Required evidence still missing: " + (", ".join(missing) or "none; lead review still needed"))
    print("This is a work summary, not a grade or hardware approval.")
    calculation_summary(session, include_missing=True)


def calculation_summary(session, include_missing=False):
    for result in session.data["computed"]:
        if result["status"] == "computed":
            print(f"\n{result['title']}: {result['value']:g} {result['units']}")
            tell("Method: " + result["method"])
            tell("Limits: " + result["limitations"])
        elif result["status"] == "invalid_inputs":
            tell(result["title"] + ": not calculated. " + result.get("error", "Check inputs."))
        elif include_missing:
            tell(result["title"] + ": not calculated; input evidence is missing.")


def open_visual(source, step):
    if not step.visual:
        print("This step has no diagram. Its explanation is above.")
        return
    try:
        path = safe_child(source.parent, step.visual)
        if not path.is_file() or path.suffix.lower() not in (".html", ".svg", ".png"):
            raise ValueError("Missing or unsupported visual.")
        if webbrowser.open(path.as_uri()):
            print("Opened the local diagram. Return here to continue.")
        else:
            print("Browser did not open. You can open this local file yourself:", path)
    except (OSError, ValueError, webbrowser.Error) as exc:
        print("Could not open the visual:", exc)
        print("You can still complete the question using the text.")


def collect(session, q, not_found=False):
    old = session.data["drafts"].get(q.id) or session.data["answers"].get(q.id, {})
    entry = {key: old[key] for key in ("value", "basis", "source", "source_revision",
                                      "assumptions", "uncertainty", "reason") if key in old}

    def field(name, prompt, required=False):
        current = entry.get(name, "")
        def save_partial(value):
            entry[name] = value
            session.draft(q.id, entry)
        while True:
            value = ask(prompt + (f" [current: {current}]" if current != "" else "") + ": ",
                        partial=save_partial)
            value = value if value else current
            if required and not str(value).strip():
                print("Please record this field, or use /skip.")
                continue
            save_partial(value)
            return value

    if not_found:
        entry.update(status="not_found", value=None)
        field("reason", "Where did you look, and what could you not find?", required=True)
        session.record(q, entry)
        print("Saved NOT FOUND and your search trail.")
        return

    entry["status"] = "answered"
    if q.kind == "choice":
        print("Options:", ", ".join(q.choices))
    if q.hint:
        tell("Hint: " + q.hint)
    while True:
        value = field("value", "Your answer" + (f" ({q.units})" if q.units else ""), required=True)
        if isinstance(value, str) and value.upper() in ("UNKNOWN", "NOT FOUND"):
            raise Command("/skip" if value.upper() == "UNKNOWN" else "/not-found")
        try:
            entry["value"] = parse_value(q, value)
            session.draft(q.id, entry)
            break
        except ValueError as exc:
            print(exc)
    if q.evidence:
        while True:
            basis = field("basis", "Basis: " + ", ".join(BASES), required=True)
            if basis in BASES:
                break
            print("Use one of the listed basis labels.")
        field("source", "Source link or document/experiment reference", required=True)
        field("source_revision", "Source date/revision and page/section (if available)")
        field("assumptions", "Assumptions (or leave blank)")
        field("uncertainty", "What is uncertain or limits this evidence?", required=True)
    session.record(q, entry)
    print("Saved your answer and evidence locally.")
    if any(q.id in c.inputs for c in session.lesson.calculations):
        calculation_summary(session)


def interview(session, source, export_root=None):
    lesson = session.lesson
    flat = [(step, q) for step in lesson.steps for q in step.questions]
    print(f"\nCORE | {lesson.id}: {lesson.title} | {lesson.minutes} minutes")
    tell("Your answers stay on this computer until you explicitly export and share them. "
         "Use only your assigned slot. Do not enter passwords, private contact details or "
         "confidential supplier messages. /help lists the controls.")
    print("Session:", session.data["session_id"], "| Slot:", session.data["participant_slot"])
    print("Saved in:", session.folder)
    for item in lesson.prerequisites:
        tell("Before you start: " + item)
    last_step = None
    try:
        while True:
            index = session.data["current_step"]
            step, q = flat[min(index, len(flat) - 1)]
            if index < len(flat):
                if step.id != last_step:
                    print("\n" + step.title.upper())
                    tell(step.teaching)
                    if step.visual:
                        print("Optional diagram: /visual")
                    last_step = step.id
                print(f"\n[{index + 1}/{len(flat)}] {q.id}: {q.prompt}")
                if q.id in session.data["answers"]:
                    a = session.data["answers"][q.id]
                    print("Saved:", a["value"] if a["status"] == "answered" else a["status"])
            try:
                if index == len(flat):
                    progress(session)
                    print("Use /edit ID to revise, /export to make a review bundle, or /quit.")
                    ask("Command: ")
                else:
                    collect(session, q)
                    session.move(index + 1)
            except Command as cmd:
                action = str(cmd)
                if action == "/help":
                    print(HELP)
                elif action == "/quit":
                    break
                elif action == "/save":
                    session.save()
                    print("Saved locally.")
                elif action == "/progress":
                    progress(session)
                elif action == "/visual":
                    open_visual(source, step)
                elif action == "/back":
                    session.move(max(0, index - 1))
                    last_step = None
                elif action == "/next":
                    session.move(min(len(flat), index + 1))
                elif action.startswith("/edit "):
                    target = action.split(maxsplit=1)[1]
                    ids = [question.id for _, question in flat]
                    if target in ids:
                        session.move(ids.index(target))
                        last_step = None
                    else:
                        print("Unknown question. Use /progress to see IDs.")
                elif action == "/skip" and index < len(flat):
                    session.record(q, {"status": "unknown", "reason": "Not researched yet"})
                    session.move(index + 1)
                elif action == "/not-found" and index < len(flat):
                    # Keep commands usable while entering the search trail.
                    try:
                        collect(session, q, not_found=True)
                        session.move(index + 1)
                    except Command as nested:
                        if str(nested) == "/quit":
                            break
                        print("Search-trail draft saved. Use /not-found to continue, or another command.")
                elif action == "/export":
                    print("Export contains completed answers, sources and assumptions, not private drafts.")
                    print("Review it for private information before sharing.")
                    print("Exported:", export_session(session, export_root))
                    print("No upload or commit was made. See SETUP.md for submission.")
                else:
                    print("Unknown/unavailable command. Use /help.")
    except (EOFError, KeyboardInterrupt):
        print("\nStopped. Accepted answers and draft fields were already saved.")
    print("Resume with --slot", session.data["participant_slot"], "--resume", session.data["session_id"])
    return 0
