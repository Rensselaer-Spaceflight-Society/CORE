"""Create two fictional student records and a lead report under ignored out/."""
from pathlib import Path
import uuid

from learning_store import PROJECT_ROOT, Session, export_session, read_json
from review import build_report
from runtime import discover


def main():
    root = PROJECT_ROOT / "out" / "learning-demo" / uuid.uuid4().hex[:10]
    lesson, _ = discover()["START1"]
    entries = read_json(Path(__file__).parent / "examples" / "fictional-answers.json")
    for slot in ("P00", "P99"):
        session = Session.create(lesson, slot, root / "drafts")
        for step in lesson.steps:
            for q in step.questions:
                entry = entries[q.id]
                if slot == "P99" and q.id == "shipping":
                    entry = dict(status="not_found", reason="FICTIONAL DEMO: searched invented quote; shipping absent.")
                session.record(q, entry)
        export_session(session, root / "submissions")
    report = build_report(root / "submissions", root / "review.html")
    print("Fictional demonstration only. No real findings or quotes were created.")
    print("Open:", report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
