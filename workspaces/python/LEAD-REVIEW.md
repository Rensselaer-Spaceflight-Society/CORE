# Reviewing a worksheet before its findings go anywhere

[Worksheets start page](README.md) · [Coordination](../coordination/README.md) · [Engineering workflow](../../docs/workflow.md)

A filled worksheet is one person's afternoon of learning, with sources attached. It is not evidence about the engine until somebody with the relevant technical role has read it and said what it is worth. This page is that step, kept short.

## Before the meeting

- Pick who gets which task code from the private roster. Task codes are what appear in the repository; names are not, and neither are anyone's stated preferences about lab work or continued participation.
- Check the worksheets still behave: `python workspaces/python/check_worksheets.py`. Fourteen lines of `ok` and you are done.
- If people need files rather than a repository: `python workspaces/python/make_bundle.py` writes a zip to `out/worksheets/`. Rebuild it after any change — a stale bundle is worse than none.
- Have one worked example ready to do on a whiteboard. Every worksheet contains one; doing it live for five minutes is worth more than any amount of written explanation.
- Nobody needs Python installed to take part. `--form` prints a paper version of any worksheet.

## The six-point check on a returned worksheet

1. **Does it run?** `python <the worksheet>`. If a student edited outside the answers block, or a lead is unsure what changed, `python workspaces/python/check_worksheets.py` re-checks every guarantee: no crash on defaults, ASCII output, no engine-model import, no file writing, unknowns still reported as unknown.
2. **Is every number's origin visible?** Value, units, source, uncertainty. A number with no source is a claim, not a finding. Send it back kindly; this is the habit the whole exercise is teaching.
3. **Are `EXAMPLE`, `CANDIDATE` and `REPO CHECK` still separate?** The commonest honest mistake is carrying an illustrative figure — an invented liner diameter, a sample loss coefficient, a made-up turbine power — forward as if it described CORE. Check especially T2, C2, C5 and C7, where the arithmetic deliberately runs on numbers the student invented.
4. **Is `NOT FOUND` recorded as a result rather than left blank?** An explicit NOT FOUND tells you where to point effort next. A blank tells you nothing. Both are fine outcomes for a first meeting; only one is useful.
5. **Does anything overreach the card?** The cards set scope deliberately narrowly. A student who has selected a bearing, chosen a casing diameter, put a number in a trip threshold, or declared a turbine material has done more than was asked and needs the boundary explained, not a scolding. Several worksheets flag this themselves — C4 objects if a threshold acquires a number, C7 objects to a zero in a cost column.
6. **Is there one question and one next step?** That is what makes the work continue. A finding with no next step tends to be the last thing that happens on that topic.

## Where a reviewed finding goes

| What you have | Where it belongs |
|---|---|
| A learning result for one task code | The Findings section of that task card. The worksheet prints it in exactly that format |
| A value two sub-teams both depend on | One row in [`workspaces/coordination/interfaces.md`](../coordination/interfaces.md), status `Candidate`, two reviewing roles |
| Missing cost or supplier information | [`workspaces/coordination/quotes.md`](../coordination/quotes.md). Never enter an unknown price as zero |
| Something that changes what the team has decided | [`workspaces/coordination/decisions.md`](../coordination/decisions.md), with the date and the evidence |
| A hazard or an uncertainty worth tracking | The [Safety](../safety/README.md) question log |

Record the review outcome and date on the card. "Reviewed, source confirmed, recorded as IF-01 candidate" is a complete review note.

## What a worksheet never does

- It does not change a design input. No worksheet imports `core/` or `modules/`, reads `config/`, or writes a file. The checker enforces all three.
- It does not produce an approved engineering result. Merging a pull request that fills in a worksheet records that a student did the work; it approves nothing.
- It does not migrate DP-2 into the model. `config/seed.yaml` still holds the earlier 250 N baseline, deliberately. Moving to DP-2 is a lead-reviewed migration that has to reconcile fixed wheel geometry, chosen mass flow, the thrust-driven M01 interface and every dependent dimension — see the [DP-2 review](../../docs/project/dp2-review.md#candidate-everyone-can-discuss).
- It does not authorise hardware. Nothing here releases a part, clears a test, or permits fuel, ignition, machining or rotor operation. Those need the applicable engineering and Safety review and the relevant shop or institutional authority — see [`docs/model-review.md`](../../docs/model-review.md#release-evidence).

## If a student's finding contradicts DP-2

That is a good day. Several worksheets are built to surface exactly this: T1 compares corrected flow against a plain unit conversion, C1 puts three different fuel numbers side by side, S2 shows that a documented "pressure recovery" is a static-to-total ratio, C6 shows a probe's headroom shrinking.

Record the contradiction with both sources and the date. Do not resolve it by picking the number you prefer, and do not close an engineering blocker because the learning task is finished. Open a [design review issue](https://github.com/Rensselaer-Spaceflight-Society/CORE/issues/new?template=design-review.yml) and let it go through the normal route.

## Keeping the worksheets healthy

The teaching scripts and the engineering solver stay apart on purpose. `check_worksheets.py` is not wired into the software CI, because a teaching script must never be able to pass or fail an engineering release check. Run it by hand when you change a worksheet or when one comes back from a student.

When a project number changes — a candidate value, a repository screen result — the worksheets that quote it need updating too. They are listed at the top of each file among the constants below the answers block, and they all cite where they came from, so they are quick to find. If you would rather a worksheet stopped quoting a moving number, delete the `ws.given(...)` line and point at the review instead.
