# Get set up and contribute

You only need Python to learn and save findings. Git and a GitHub account are optional until you submit work yourself. Keep the project in a local folder outside OneDrive when possible.

## Windows: install missing tools once

Run these in PowerShell only for tools you do not already have:

```powershell
winget install --exact --id Python.Python.3.13 --source winget
winget install --exact --id Git.Git --source winget
winget install --exact --id GitHub.cli --source winget
```

Close and reopen PowerShell after installing. Installers may ask for permission. If winget is unavailable or your computer is managed, use official installers/campus IT; do not change machine security settings to get around restrictions. [WinGet documentation](https://learn.microsoft.com/en-us/windows/package-manager/winget/install).

Clone into a **new** directory; do not replace an existing copy with unsaved work:

```powershell
py -3.13 --version
git --version
git clone https://github.com/Rensselaer-Spaceflight-Society/CORE.git "$env:USERPROFILE\CORE-student"
Set-Location "$env:USERPROFILE\CORE-student"
py -3.13 workspaces/python/interactive/launch.py
```

Before the foundation is merged, use `git clone --branch feat/guided-learning-platform` with the same URL/destination instead. After merge, the command above uses current main. If Python 3.11/3.12 is already installed, use that installed version instead of 3.13. No pip install is needed for guided lessons.

Choose START1 initially, then enter your assigned slot such as P01. The launcher lists new topic lessons as they are installed. You can also run your assigned lesson's Python file directly.

## macOS / Linux

Use a supported Python 3.11–3.13 installation and Git. macOS users can use the [official Python installer](https://docs.python.org/3.13/using/mac.html); do not remove Apple's system Python. Linux users should use their distribution/campus-supported installation, checking the version before continuing. GitHub CLI is optional; use GitHub's website to open a PR if it is not installed.

```sh
python3 --version
git --version
git clone https://github.com/Rensselaer-Spaceflight-Society/CORE.git "$HOME/CORE-student"
cd "$HOME/CORE-student"
python3 workspaces/python/interactive/launch.py
```

For the unmerged foundation use the branch option described above. These shell snippets require an empty/new destination. The distribution ZIP is an equally valid way to obtain and run the lessons.

## Stop, resume, export

- `/quit` stops; accepted answers and draft fields are already saved locally.
- Run the same command and enter the same slot to choose a saved session.
- `/export` creates a **new** folder beneath `workspaces/submissions/<slot>/<lesson>/`. The program prints its path. Review its `summary.md` and `answers.json` before sharing. Unfinished drafts are excluded.
- Send that entire export folder to the lead if you do not want to use Git. A ZIP attachment through your team's agreed channel is fine; the program does not send it for you.
- Export again after later edits; it creates another snapshot rather than replacing the previous one.

Explicit resume/recovery commands (replace SESSION_ID with the actual printed ID):

```powershell
py -3.13 workspaces/python/interactive/launch.py --list-sessions --slot P01
py -3.13 workspaces/python/interactive/launch.py --lesson START1 --slot P01 --resume SESSION_ID
py -3.13 workspaces/python/interactive/launch.py --lesson START1 --slot P01 --recover SESSION_ID
```

Recovery copies the newest valid history snapshot into a new session, preserving the old files. If two windows opened the same session, close the other window before continuing. A rejected write is not saved; retain the entry and reopen the latest session. A changed lesson version needs its original bundle or a new session.

## GitHub access: one-time setup

A repository administrator can give students **Write** access through a team or collaborator invitation, which the student must accept. This allows personal branches; keep main protected. Read/Triage access does not grant push permission. [Repository roles](https://docs.github.com/en/organizations/managing-user-access-to-your-organizations-repositories/managing-repository-roles/repository-roles-for-an-organization).

Inside the clone, if GitHub CLI is installed:

```sh
gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git
gh auth status
git config user.name "Your own commit display name"
git config user.email "Your verified GitHub email or noreply email"
gh api repos/Rensselaer-Spaceflight-Society/CORE --jq '.permissions.push'
```

Replace the two identity strings with your own details; these are repository-local settings. Git identity does not authenticate you. The final command checks the logged-in account's push permission; it cannot grant access. Never share a token or another person's account. [CLI authentication setup](https://cli.github.com/manual/gh_auth_setup-git).

Without Write access, you can make a fork, if permitted:

```sh
gh repo fork --remote=true --clone=false
git remote -v
```

Read the output: this workflow normally makes your fork `origin` and the shared repository `upstream`. Confirm before pushing. If no fork is available, use lead-assisted submission. [CLI fork workflow](https://cli.github.com/manual/gh_repo_fork).

## Submit on your own branch

For a **new** task, first commit or otherwise preserve existing work and confirm `git status` is clean. Do not switch branches or pull over unsaved changes. Replace P07 below with your slot and choose a unique branch suffix:

```sh
git status
git fetch https://github.com/Rensselaer-Spaceflight-Society/CORE.git main
git switch -c findings/P07-session-01 FETCH_HEAD
```

Until the foundation merges, fetch `feat/guided-learning-platform` instead of `main`. Continue existing work on its existing branch. Run your lesson and export, then replace the example path below with the **exact export folder printed by the program**:

```sh
git add -- workspaces/submissions/P07/START1/EXACT-EXPORTED-FOLDER
git diff --cached --stat
git commit -m "START1: record research findings"
git push -u origin HEAD
gh pr create --repo Rensselaer-Spaceflight-Society/CORE --base main --web
```

The example export path is a placeholder, not a real folder. If CLI is unavailable, use GitHub's “Compare & pull request” after the push. From a fork, select your fork/branch as the source. While foundation is unmerged, coordinate the PR base with the lead to avoid duplicating its changes. No auto-commit/upload happens when you run a lesson.

## Fifteen students at once

Use one work branch and unique export directories per participant/session. Different files normally merge cleanly; overlapping edits, shared branches and shared result files increase conflicts. Keep lesson source edits separate from routine answers. The review report is generated locally and is not a shared file everyone edits. Conflicting engineering claims still need discussion even when Git merges perfectly. [Merge conflicts](https://docs.github.com/en/pull-requests/reference/merge-conflicts).

Do not use force-push or “accept ours/theirs” to discard a student's work. Ask a lead to help reconcile the branch if Git reports a conflict.

| Problem | What to check |
|---|---|
| “Author identity unknown” during commit | Configure your local Git name/email; this is not a remote permission failure |
| 403 / permission denied during push | Correct account, invitation accepted, Write role, organization sign-on rules, correct remote |
| Protected-main rejection | Push a personal branch and open a PR; keep protection |
| Non-fast-forward rejection | That branch has new commits elsewhere; preserve your work and reconcile with help |
| Python opens the Store / not found | Reopen the terminal; use the installed `py` version or Python executable |
| Save permission error | Keep previous records; use a writable local folder or an explicit `--data-dir` |
| No terminal input / editor “Run output” pane | Run from an actual terminal; `--preview` is read-only and works without input |
| Lost/corrupt current session | Preserve the folder; try `--recover` rather than deleting it |

Send the exact command/error to your lead, with credentials/private paths removed. A local **commit** and a remote **push** are different steps.

## No installation today

Use the offline bundle on a campus machine, or ask someone to print `launch.py --lesson START1 --preview`. Submit notes through your lead. Keep the entire extracted folder intact. A useful finding matters more than completing account setup during a meeting.
