"""Check every first-meeting worksheet still behaves. For leads and reviewers.

Run it from anywhere:

    python workspaces/python/check_worksheets.py

It runs each worksheet three ways - normally, with --form and with --help -
and checks the properties the worksheets are supposed to guarantee:

  1. it runs to completion with nobody's answers filled in,
  2. its output is plain ASCII, so redirecting it to a file cannot fail,
  3. an untouched worksheet never reports itself ready for review,
  4. unknown entries are still reported as unknown,
  5. it does not import the engine model in core/ or modules/,
  6. it does not open or write any file.

Exit status 0 means everything passed. Run this before merging a change to
the worksheets, and after a student sends one back, so that a stray edit
cannot quietly turn a teaching script into something else.

This checker is deliberately not part of the engineering CI gate. A worksheet
is teaching material; it must never be able to pass or fail an engineering
release check.
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEAMS = ("turbomachinery", "structures", "combustion-systems")

# U+FFFD, what a non-ASCII byte turns into when we decode the output as ASCII.
REPLACEMENT_CHARACTER = "�"

FORBIDDEN_IMPORTS = (
    "import core", "from core", "import modules", "from modules",
    "import run", "from run",
)
FORBIDDEN_WRITES = (
    "open(", "write_text(", "write_bytes(", "os.remove", "shutil.",
    "os.rename", "os.mkdir", "makedirs",
)


def worksheets():
    found = []
    for team in TEAMS:
        folder = HERE / team
        if not folder.is_dir():
            continue
        found.extend(sorted(p for p in folder.glob("*.py")
                            if not p.name.startswith("_")))
    return found


def run(path, args):
    return subprocess.run(
        [sys.executable, str(path)] + list(args),
        capture_output=True, text=True, encoding="ascii", errors="replace")


def check(path):
    """Return a list of problems. An empty list means the worksheet is fine."""
    problems = []
    source = path.read_text(encoding="utf-8")

    if not source.isascii():
        problems.append("source is not plain ASCII")

    for needle in FORBIDDEN_IMPORTS:
        if needle in source:
            problems.append(
                "imports the engineering model ('{0}'). Teaching worksheets "
                "must stay separate from the solver.".format(needle))
    for needle in FORBIDDEN_WRITES:
        if needle in source:
            problems.append(
                "looks like it writes a file ('{0}'). Worksheets print; they "
                "do not save.".format(needle))
    if "YOUR ANSWERS" not in source:
        problems.append("has no block marked YOUR ANSWERS")
    if "ws.finish()" not in source:
        problems.append("never calls ws.finish(), so it prints no report")
    if "done_when" not in source:
        problems.append("never says what 'done' means")

    default = run(path, [])
    if default.returncode != 0:
        problems.append("exit status {0} with nobody's answers filled in:\n{1}"
                        .format(default.returncode, default.stderr.strip()))
        return problems
    if REPLACEMENT_CHARACTER in default.stdout:
        problems.append("printed a character that is not ASCII")
    if "Ready for lead review" in default.stdout:
        problems.append("reports itself ready for review before anybody has "
                        "filled it in")
    if "NOT RECORDED" not in default.stdout and "NOT FOUND" not in default.stdout:
        problems.append("does not report its unknown entries as unknown")
    if "Traceback" in default.stderr:
        problems.append("printed a traceback")

    form = run(path, ["--form"])
    if form.returncode != 0:
        problems.append("--form failed: {0}".format(form.stderr.strip()))
    elif "Date:" not in form.stdout:
        problems.append("--form did not print a usable blank form")

    help_run = run(path, ["--help"])
    if help_run.returncode != 0:
        problems.append("--help failed: {0}".format(help_run.stderr.strip()))

    return problems


def main():
    found = worksheets()
    if not found:
        print("No worksheets found under {0}".format(HERE))
        return 1

    failures = 0
    for path in found:
        problems = check(path)
        label = "{0}/{1}".format(path.parent.name, path.name)
        if problems:
            failures += 1
            print("FAIL  {0}".format(label))
            for problem in problems:
                print("        - {0}".format(problem))
        else:
            print("ok    {0}".format(label))

    print("")
    print("{0} worksheet(s) checked, {1} problem(s).".format(len(found), failures))
    if failures:
        print("A filled worksheet is still only learning evidence. Fix the "
              "problems above before it goes anywhere near the design record.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
