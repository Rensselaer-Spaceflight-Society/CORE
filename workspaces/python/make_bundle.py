"""Build a starter bundle of the first-meeting worksheets. For leads.

Most people should just use GitHub's green Code button and "Download ZIP",
which gives them the whole repository including these worksheets. This script
exists for the other cases: handing one person one worksheet, putting a small
folder on a memory stick, or attaching something to a message for people who
will never open GitHub.

    python workspaces/python/make_bundle.py              everything, one zip
    python workspaces/python/make_bundle.py --task T1    one worksheet
    python workspaces/python/make_bundle.py --each       one zip per task code

Bundles are written to out/worksheets/, which is not tracked by Git, so
nothing here can go stale inside the repository. Rebuild whenever the
worksheets change.

The bundle is flat: every worksheet sits next to worksheet_common.py, which
is all the worksheets need to run. A student can unzip it anywhere.
"""

import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = REPO / "out" / "worksheets"
TEAMS = ("turbomachinery", "structures", "combustion-systems")
SUPPORT = ("worksheet_common.py", "README.md", "HOW-TO-RUN.md")

READ_ME_FIRST = """CORE first-meeting Python worksheets
====================================

You need Python 3.11 or newer. Check with:   python --version

Then run your worksheet. For example:

    python t1_compressor_map.py

Read what it prints. Open the same file in any text editor, fill in the block
marked YOUR ANSWERS, save it, and run it again. It will tell you what is
still missing.

No Python on the machine in front of you? Run this instead on any machine
that has it, and fill the result in on paper:

    python t1_compressor_map.py --form

Keep worksheet_common.py in the same folder as your worksheet. Everything
else in here is documentation.

Full instructions, including how to send your work back:  HOW-TO-RUN.md

A filled worksheet is learning evidence. It is not an approved engineering
result and it does not authorise anything.
"""


def worksheets():
    found = []
    for team in TEAMS:
        folder = HERE / team
        if folder.is_dir():
            found.extend(sorted(p for p in folder.glob("*.py")
                                if not p.name.startswith("_")))
    return found


def task_code(path):
    """T1 from t1_compressor_map.py, C3 from c3_fuel_blocks.py."""
    stem = path.name.split("_")[0]
    return stem.upper()


def missing_support():
    return [name for name in SUPPORT if not (HERE / name).is_file()]


def build(name, paths):
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / name
    root = target.stem
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("{0}/READ-ME-FIRST.txt".format(root), READ_ME_FIRST)
        for support in SUPPORT:
            source = HERE / support
            if source.is_file():
                bundle.write(source, "{0}/{1}".format(root, support))
        for path in paths:
            bundle.write(path, "{0}/{1}".format(root, path.name))
    size_kb = target.stat().st_size / 1024.0
    print("  {0}  ({1} worksheet(s), {2:.0f} kB)".format(
        target.relative_to(REPO), len(paths), size_kb))
    return target


def main(argv):
    found = worksheets()
    if not found:
        print("No worksheets found under {0}".format(HERE))
        return 1

    absent = missing_support()
    if absent:
        print("Warning: not bundling missing support file(s): {0}"
              .format(", ".join(absent)))

    wanted = None
    if "--task" in argv:
        index = argv.index("--task")
        if index + 1 >= len(argv):
            print("--task needs a task code, for example: --task T1")
            return 2
        wanted = argv[index + 1].upper()

    print("Writing bundles to {0}".format(OUT))
    if wanted:
        chosen = [p for p in found if task_code(p) == wanted]
        if not chosen:
            print("No worksheet for task code '{0}'. Available: {1}".format(
                wanted, ", ".join(sorted(task_code(p) for p in found))))
            return 2
        build("core-worksheet-{0}.zip".format(wanted), chosen)
    else:
        build("core-python-worksheets.zip", found)
        if "--each" in argv:
            for path in found:
                build("core-worksheet-{0}.zip".format(task_code(path)), [path])

    print("")
    print("Hand these out however suits the team. Rebuild after any change to")
    print("the worksheets - a stale bundle is worse than no bundle.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
