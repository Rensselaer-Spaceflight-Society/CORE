"""Build an offline guided-lesson ZIP; never bundles student records or caches."""
import argparse
from pathlib import Path
import zipfile

from learning_store import PROJECT_ROOT, revision

HERE = Path(__file__).resolve().parent


def build(output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as bundle:
        for source in sorted(HERE.rglob("*")):
            if (source.is_file() and not source.is_symlink() and "__pycache__" not in source.parts
                    and source.suffix in (".py", ".md", ".json", ".html", ".svg", ".png")):
                bundle.write(source, "CORE-learning/" + source.relative_to(PROJECT_ROOT).as_posix())
        for name in ("docs/project/dp2-review.md", "docs/project/budget-cap.md"):
            source = PROJECT_ROOT / name
            if source.exists():
                bundle.write(source, "CORE-learning/" + name)
        bundle.writestr("CORE-learning/SOURCE-REVISION.txt", revision() + "\n")
        bundle.writestr("CORE-learning/START-HERE.txt",
                        "CORE guided research (Python 3.11-3.13; no extra packages)\n\n"
                        "Unzip the whole folder. Open a terminal in CORE-learning.\n"
                        "Windows: py -3.13 workspaces/python/interactive/launch.py\n"
                        "macOS/Linux: python3 workspaces/python/interactive/launch.py\n"
                        "Choose START1 for the working example. Use your assigned slot, e.g. P01.\n"
                        "Questions save locally; /quit stops; rerun to resume. /export creates\n"
                        "a shareable folder under workspaces/submissions. Nothing uploads itself.\n"
                        "No Python today? Read the lesson script or use --preview on a campus PC.\n"
                        "Keep this folder intact. See workspaces/python/interactive/SETUP.md.\n")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "out" / "worksheets" / "core-guided-learning.zip")
    print(build(parser.parse_args().output))
