"""START1: a working example and useful first evidence record. No packages."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from runtime import Calculation, Lesson, Question, Step, run_lesson


def build_lesson():
    return Lesson(
        id="START1", version="1.0", title="Turn one research finding into useful evidence",
        review_role="Assigned sub-team lead", minutes="30-45",
        prerequisites=("Pick one small question from your current assignment with your lead.",
                       "Use a public document or a non-confidential reference. No hardware is needed."),
        sources=("docs/project/dp2-review.md", "docs/project/budget-cap.md"),
        steps=(
            Step("purpose", "1. What will your finding help decide?",
                 "Think of evidence as a labeled ingredient. A number without its source and "
                 "units is like an unmarked jar: nobody can safely use it. Pick ONE useful "
                 "question, such as whether a sensor has an electrical output or whether a "
                 "stock size is available. CORE's $5,000 cap is a constraint; its DP-2 engine "
                 "numbers are proposals under review. You do not need to confirm them.",
                 (Question("target", "What specific part, input or decision are you investigating?",
                           evidence=False, hint="Use the exact part number or interface if you know it."),),
                 visual="evidence.html"),
            Step("evidence", "2. Find one thing somebody else can check",
                 "Start with a manufacturer datasheet, drawing revision or documented experiment. "
                 "Record what it actually supports, including conditions. A sensor's supply "
                 "voltage does not tell you its output voltage. A wheel diameter does not prove "
                 "that another wheel's map applies. EXAMPLE means teaching only; CANDIDATE "
                 "means proposed; SOURCED means documented; MEASURED means observed in a "
                 "described experiment. None of those words means approved. If you looked and "
                 "could not find the information, /not-found records that useful result.",
                 (Question("finding", "What did you find, in your own words?",
                           hint="Include units and conditions for numbers; use /text for several lines."),)),
            Step("cost", "3. Optional: what would this item cost to arrive?",
                 "If your question is about buying an item, record a price and shipping for the "
                 "same quantity and currency. This example uses USD. For example only, a $10 "
                 "item plus $3 shipping is $13 before taxes. These are invented teaching values, "
                 "not CORE quotes. If cost is irrelevant, /skip both questions. Missing shipping "
                 "is UNKNOWN, not zero. The calculation excludes taxes, duties and other items.",
                 (Question("price", "Item subtotal for the quoted quantity (optional)",
                           kind="number", units="USD", minimum=0, required=False),
                  Question("shipping", "Shipping for that same quote (optional)",
                           kind="number", units="USD", minimum=0, required=False))),
            Step("handoff", "4. Make the next conversation easier",
                 "Your lead needs the finding, its limits and the next decision. You do not "
                 "need to solve the whole engine. A good next step might be finding the exact "
                 "part's datasheet or asking the lead which drawing revision is current. "
                 "Do not purchase or change an engineering input because this lesson is done.",
                 (Question("lead_question", "What question or decision needs the lead's attention?",
                           evidence=False, role="decision"),
                  Question("next_step", "What is your next small research step?",
                           evidence=False, role="next_step"))),
        ),
        calculations=(Calculation("subtotal", "Item plus shipping, before taxes/duties",
                                  ("price", "shipping"), lambda price, shipping: price + shipping,
                                  units="USD", method="subtotal = price + shipping", version="1",
                                  limitations="Same quote quantity and currency required. Excludes taxes, "
                                  "duties and other items; not a complete project budget."),),
    )


if __name__ == "__main__":
    raise SystemExit(run_lesson(build_lesson(), __file__))
