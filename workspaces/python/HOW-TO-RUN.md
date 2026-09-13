# How to run a worksheet, save it, and send it back

[Worksheets start page](README.md) · [First-meeting workspace](../README.md)

Four steps: get the file, run it, fill it in, send it back. None of them needs previous experience, and the last one has a route that needs no GitHub account at all.

## 1. Get the file

**Easiest:** on the repository's front page, click the green **Code** button and then **Download ZIP**. Unzip it. Your worksheet is in `workspaces/python/<your team>/`.

**If your lead handed you a zip:** unzip it anywhere. Everything you need is in one folder.

**If you already use Git:** clone the repository as normal.

Keep `worksheet_common.py` wherever it came from relative to your worksheet. It is the small shared file every worksheet uses. If you move one worksheet somewhere on its own it will tell you so in plain language rather than crashing.

## 2. Run it

First check you have Python 3.11 or newer:

```bash
python --version
```

If that says something older, or "command not found", see [No Python today?](#no-python-today) below — you can still do the whole activity.

Then run your worksheet. Use the path to the file:

```bash
python workspaces/python/turbomachinery/t1_compressor_map.py
```

On Windows, `py` sometimes works where `python` does not:

```powershell
py workspaces\python\turbomachinery\t1_compressor_map.py
```

You should get a page or two of text: an explanation, a worked example, a calculation section, a list of what is still blank, and a block to paste into your card. That is the worksheet working correctly with nothing filled in. Read it through once before you touch anything.

## 3. Fill it in

Open the same file in any text editor. Notepad, TextEdit, VS Code, IDLE, whatever you have. It is a plain text file.

Near the top you will find:

```python
# ===========================================================================
#  YOUR ANSWERS - this is the only part of the file you need to edit.
# ===========================================================================
```

Everything between there and `END OF YOUR ANSWERS` is yours. Below it, you do not need to change anything.

Replace `UNKNOWN` with what you found. Text goes in quotes; numbers do not:

```python
EXACT_PART = answer(
    value="Garrett GT3076R, part number 700177-5011",
    source="https://example.com/the-page-I-actually-read",
    uncertainty="several billet copies exist under other names",
)

MAP_REF_TEMPERATURE_K = answer(
    value=288.15,
    units="K",
    source="stated on the map itself, bottom left",
)
```

Looked and genuinely could not find it? Write `NOT_FOUND`, with no quotes:

```python
RATED_SPEED_RPM = answer(
    value=NOT_FOUND,
    units="rpm",
    source="checked the catalogue and two vendor pages; not published",
)
```

Save, and run it again. It will pick up what you wrote and tell you what is still missing.

### If something goes wrong

| What you see | What it usually means |
|---|---|
| `SyntaxError: ... unterminated string literal` | A quote mark is missing at one end of some text |
| `SyntaxError: invalid syntax` | A comma is missing at the end of a line, or a bracket is unclosed |
| `NameError: name 'Garrett' is not defined` | Text was typed without quotes around it |
| `could not be read as a number` | Units got typed inside the value: write `288.15`, not `288.15 K` |
| `Could not find worksheet_common.py` | The worksheet got separated from its shared file — put it back, or re-download |

Nothing you can type will damage anything. If a file gets into a state you cannot untangle, download a fresh copy and paste your answers across.

## 4. Send it back

Pick whichever of these three suits you. They are equally welcome, and the first one is the one most people should use at a first meeting.

### Route A — paste a finding, no Git needed

Run your worksheet, copy the block it prints under **PASTE THIS INTO YOUR CARD**, and put it into a [first-meeting finding issue](https://github.com/Rensselaer-Spaceflight-Society/CORE/issues/new?template=meeting-finding.yml). Enter your task code, not your name.

A GitHub account is needed to open an issue. If you do not have one and do not want one today, use Route B.

### Route B — lead-assisted, no account needed

Send your lead either the whole edited `.py` file, or just the block it printed. They will check it and put it where it belongs. This is a completely normal way to contribute and nobody should spend the meeting fighting with account setup.

Your lead: see [LEAD-REVIEW.md](LEAD-REVIEW.md) for what to check first.

### Route C — propose the change yourself

If you are comfortable with GitHub, or want to learn:

1. On the repository page, find your worksheet and click the pencil (Edit) icon. GitHub will offer to fork the repository for you — accept.
2. Paste your answers into the `YOUR ANSWERS` block. Change nothing else.
3. Below the editor, choose "Create a new branch for this commit and start a pull request".
4. Title it with your task code and what you did, for example `T1: identify compressor map source`.
5. Open the pull request. Your lead reviews it.

From a clone instead:

```bash
git switch -c t1-compressor-map-finding
# edit your worksheet, then
git add workspaces/python/turbomachinery/t1_compressor_map.py
git commit -m "T1: record compressor map source and reference conditions"
git push -u origin t1-compressor-map-finding
```

Then open a pull request on GitHub.

**Change only your own worksheet.** Do not edit somebody else's, and do not touch anything in `config/`, `core/` or `modules/` — that is the engineering model, and it has its own review process in [CONTRIBUTING.md](../../CONTRIBUTING.md).

## Saving the output

The simplest thing is to select the text in your terminal and copy it. That is what most people should do.

If you would rather have a file:

```bash
# macOS, Linux, Git Bash
python workspaces/python/turbomachinery/t1_compressor_map.py > T1-findings.txt
```

```powershell
# Windows PowerShell
python workspaces\python\turbomachinery\t1_compressor_map.py | Out-File -Encoding utf8 T1-findings.txt
```

Worksheet output is plain ASCII, so this works everywhere without encoding trouble.

## No Python today?

You can do the entire activity without it. The engineering is the point; the script is a convenience.

**Printed form.** Anyone with Python — your lead, a teammate, a lab machine — can produce a blank paper form for any worksheet:

```bash
python workspaces/python/turbomachinery/t1_compressor_map.py --form
```

That prints the same questions with lines to write on. Print it, fill it in by hand, hand it to your lead.

**Read it on GitHub.** Click the worksheet file on GitHub and read it in the browser. The lesson is in the comments and the `YOUR ANSWERS` block shows exactly what is being asked for. Write your answers in a document, an email or a notebook using the same labels.

**Paper or a shared document.** Use the task-code headings and the fields the worksheet asks for: value, units, source, how sure you are. Your lead collects them the same way.

If you want Python afterwards, [python.org/downloads](https://www.python.org/downloads/) has it for every platform. On Windows, tick "Add Python to PATH" during installation. You need nothing else — no packages, no accounts, no virtual environment. The worksheets use only what comes with Python.

## What a filled worksheet is, and is not

It is learning evidence, with its sources and assumptions attached. That is genuinely valuable and it is what was asked for.

It is not an approved engineering result, it does not set a design value, and it authorises nothing. A merged pull request does not change that either. Findings enter the shared design record only when a lead reviews them and records them deliberately — see [LEAD-REVIEW.md](LEAD-REVIEW.md).
