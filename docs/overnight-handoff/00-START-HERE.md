# CORE overnight engineering handoff

Prepared October 4, 2026. Budget confirmed by the user in this conversation: **aim for $5,500 total cash; $6,000 maximum ceiling**. This supersedes the older $5,000 repository cap and the October 2 workbook's $5,950 target for this assignment.

Give the next agent the entire `docs/overnight-handoff/` folder and repository access. The master prompt is the execution instruction; the other files supply its checklist, context and acceptance details. This packet prepares work; it does not start an agent, schedule an overnight run, approve a purchase or release hardware.

| File | Use |
|---|---|
| [01-MASTER-PROMPT.md](01-MASTER-PROMPT.md) | Complete instruction to execute the work autonomously |
| [02-TASKS-AND-ACCEPTANCE.md](02-TASKS-AND-ACCEPTANCE.md) | Ordered tasks with dependencies and concrete completion checks |
| [03-CONTEXT-AND-SOURCES.md](03-CONTEXT-AND-SOURCES.md) | Existing results, current budget, source hierarchy and research starting points |
| [04-OUTPUT-CONTRACTS.md](04-OUTPUT-CONTRACTS.md) | Minimum content for component designs, CAD handoff, verification and the morning report |
| [Earlier survey](../preliminary-design-roadmap.md) | Full source-code map and preliminary completion order |

The intended result is a working, reproducible candidate engine definition with connected components, preliminary CAD parameters, a manufacturing/cost assessment and an honest assessment of self-sustain feasibility. The agent should implement code and perform defensible preliminary calculations, rather than return another plan or merely create empty interfaces. The team will perform the detailed engineering analyses and native CAD integration.

The inspected source revision is `98c4167`. The earlier survey and this packet are local additions; include them explicitly if transferring a clean checkout. A new worktree created from a commit alone may omit them. Do not assume the recipient has this conversation or the neighboring budget workbook.

The authoritative local working directory is:

`C:\Users\andyc\OneDrive\Desktop\CORE\github-core`

The latest supporting budget workbook is outside the repository:

`C:\Users\andyc\OneDrive\Desktop\CORE\outputs\core-budget-20261002-fbef9859\CORE_Itemized_Budget.xlsx`

Its material findings are summarized in the context file so work can continue without the workbook. Exact item rows and formulas should be read from the workbook when available. Preserve the original workbook.

Use this dispatch message after giving the agent access:

> Work in `C:\Users\andyc\OneDrive\Desktop\CORE\github-core`. Read and execute `docs/overnight-handoff/01-MASTER-PROMPT.md` and its three companion files. Implement the work, run the checks, and produce the connected preliminary design and review packet. The current budget is a $5,500 target with a $6,000 hard total ceiling. Prioritize a defensible self-sustain candidate using the purchased turbine/NGV route recorded in the current project materials. Make reversible candidate decisions and keep working through independent tasks when a fact is missing. Preserve engineering unknowns, existing user work and the distinction between preliminary calculation and demonstrated operation. Return the morning report with exact run commands, artifacts, verified results, cost gaps and the remaining decisions that need the team.

If the agent runs elsewhere, replace the workspace path. Do not infer a time limit, token budget or recurring schedule from “overnight.” Use the time/resource allowance actually available and keep resumable progress. Native CAD and specialist solver availability should not block the core implementation.
