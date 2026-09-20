"""C2-FAB - Track B: a fabrication demonstrator somebody can actually build.

Run it:  python workspaces/python/interactive/lessons/structures/fabrication_coupon.py
Preview: same command with --preview  (read-only, writes nothing)

For the member with welding experience. The output is a buildable, inspectable
process and a list of decisions the team owes an answer to - not another
general alloy essay.

Extends C2 (shop capability) into the structures track; see
workspaces/structures/TASK-CODE-MAP.md. It releases nothing: not the turbine,
not a pressure-retaining casing, not fuel-containing parts, and not a welding
procedure.
"""

from pathlib import Path
import sys

_HERE = Path(__file__).resolve().parent
for _folder in (_HERE.parents[1], _HERE):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

from runtime import Calculation, Lesson, Question, Step, run_lesson  # noqa: E402
import _structures_math as sm  # noqa: E402


def build_lesson():
    return Lesson(
        id="C2-FAB", version="1.0",
        title="A fabrication demonstrator you can build, measure and argue about",
        review_role="Structures lead with the shop/welding authority; "
                    "Chief engineer for any spending; Safety before anything runs",
        minutes="30-45",
        prerequisites=(
            "This lesson is written for someone who has actually welded. If that "
            "is not you, do it with the person who has - their hands-on judgement "
            "is the input here, not a search engine's.",
            "Desk work only. No shop entry, no forming, no welding, no cutting and "
            "no purchase today. Later practical work needs the normal shop "
            "prerequisites and the shop's own authority.",
            "Do NOT send any message to a supplier, the shop or the welding "
            "authority because of this lesson. You are writing questions down, "
            "not asking them. The lead arranges contacts.",
        ),
        sources=(
            "AWS D17.1/D17.1M:2024, Specification for Fusion Welding for Aerospace "
            "Applications (4th ed., approved 25 March 2024). Scope 1.1: "
            "'requirements for fusion welding and nondestructive examination (NDE) "
            "of aerospace flight hardware as well as for the welding and NDE of "
            "non-flight hardware.' It keeps welding procedure qualification (5.2), "
            "welder/operator/tack-welder performance qualification (5.3-5.4) and "
            "production welding (Clause 6) as separate things. "
            "https://pubs.aws.org/p/2236/d171d171m2024-specification-for-fusion-welding-for-aerospace-applications",
            "TWI Job Knowledge 33, 'Distortion - types and causes': longitudinal and "
            "transverse shrinkage, angular distortion, bowing and dishing, buckling "
            "in thin plate, twisting; and that restraint cuts distortion at the cost "
            "of higher residual stress. "
            "https://www.twi-global.com/technical-knowledge/job-knowledge/distortion-types-and-causes-033",
            "F. Armao, 'Which filler wire is best for welding 6061-T6 aluminum, 5356 "
            "or 4043?', The Welder, 3 October 2006. TRADE GUIDANCE, not a "
            "specification: 5356 has roughly 50% higher shear strength; 4043 is less "
            "crack-sensitive and is preferred above about 150 F service; a 6061-T6 "
            "butt weld fails in the heat-affected zone either way; 4043 anodises "
            "black. "
            "https://www.thefabricator.com/thewelder/article/aluminumwelding/which-filler-wire-is-best-for-welding-6061-t6-aluminum-5356-or-4043r",
            "docs/project/budget-cap.md - the $5,000 cash ceiling, the spending "
            "envelopes, and the rule against counting a donation twice",
            "workspaces/coordination/quotes.md - where a shareable quote summary goes",
            "config/limits.yaml - casing_fit_margin_min_m = 0.002, the radial "
            "clearance the combustor needs inside the casing bore",
            "workspaces/combustion-systems/C2-fabrication.md - the shop-capability "
            "card this lesson extends",
        ),
        steps=(
            Step(
                "demonstrator", "1. Pick one thing worth building this month",
                "The team cannot build a turbine yet, and should not. But there is "
                "a large amount of nonrotating sheet metal in a reverse-flow engine "
                "- the outer casing, the liner, the inlet, brackets, the stand - and "
                "almost every question about whether the team can make those parts "
                "is answerable now, cheaply, on scrap, with nothing spinning.\n\n"
                "So: propose ONE demonstrator. A rolled-and-seam-welded cylinder "
                "section in the casing's gauge and alloy. A formed flange with the "
                "actual bend radius. A drilled-and-welded boss in liner-gauge sheet. "
                "Something small, made from the real stock by the real process, "
                "that answers a real question.\n\n"
                "The test of a good demonstrator is what it tells you that you did "
                "not already know. 'Can we roll this gauge to this diameter with the "
                "tooling we have, and how much does the seam pull it out of round?' "
                "is a question with an answer and a consequence. 'Can we weld "
                "aluminium?' is not.\n\n"
                "Be explicit about what this is NOT. A coupon is not a qualified "
                "welding procedure, not a pressure-rated component, and not a "
                "released part. Nothing here touches the turbine, a "
                "pressure-retaining casing for a running engine, or anything that "
                "contains fuel.",
                (
                    Question(
                        "demonstrator_part",
                        "What is your proposed demonstrator, in one sentence?",
                        evidence=False,
                        hint="Concrete beats general. 'A 120 mm long rolled cylinder section "
                             "in 1.5 mm 6061, one longitudinal seam, no holes' is a "
                             "demonstrator. 'A test piece' is not.",
                    ),
                    Question(
                        "informs_what",
                        "Which real build decision does it inform, and how?",
                        evidence=False,
                        hint="Name the part and the decision. 'Whether the 1.5 mm casing wall "
                             "can be rolled and seam welded to within the 2 mm radial "
                             "clearance the liner needs' ties it to config/limits.yaml.",
                    ),
                    Question(
                        "explicitly_not",
                        "State what this demonstrator will NOT establish.",
                        evidence=False, role="decision",
                        hint="Write it down now, before anyone over-reads the result later. "
                             "Procedure qualification, pressure rating, fatigue life, "
                             "material certification - which of these are you NOT claiming?",
                    ),
                ),
                visual="coupon_plan.html",
            ),
            Step(
                "stock", "2. What stock can you actually get, in what size, by when",
                "Fabrication feasibility usually dies on availability, not on "
                "theory. Before the process question there is a stock question: "
                "what alloy and temper, what gauge, what sheet size, what minimum "
                "order, what lead time, and how much of it turns into scrap.\n\n"
                "ALLOY AND TEMPER ARE BOTH PART OF THE ANSWER. 6061-T6 and 6061-O "
                "are the same alloy with very different strength, formability and "
                "behaviour after welding. A bend radius that works annealed will "
                "crack in T6. Say which you are costing.\n\n"
                "FORMING LIMITS. Sheet has a minimum bend radius that depends on "
                "alloy, temper, thickness and bend direction relative to the "
                "rolling grain. Bending across the grain and bending along it are "
                "not the same operation. Get the supplier's or the shop's actual "
                "figure rather than a remembered rule.\n\n"
                "SCRAP IS NOT PESSIMISM, IT IS PLANNING. Edge trim, nesting waste, "
                "clamp land, the setup piece you ruin getting the machine right, "
                "and at least one coupon you will want to cut up and look at. "
                "docs/project/budget-cap.md is blunt about the cost of pretending "
                "otherwise: never record an unknown price as zero.",
                (
                    Question(
                        "stock_alloy",
                        "Candidate alloy AND temper, with the evidence you have for availability",
                        hint="Both parts. If you only know 'aluminium sheet', that is UNKNOWN, "
                             "not 6061-T6.",
                    ),
                    Question(
                        "stock_gauge",
                        "Sheet thickness you would buy",
                        kind="number", units="mm", minimum=0, maximum=100,
                        hint="Say in 'assumptions' whether this matches the casing wall the "
                             "model uses (config/seed.yaml casing_wall_m) or differs, and why.",
                    ),
                    Question(
                        "forming_limit",
                        "Minimum bend radius for that stock, and where the figure came from",
                        hint="Include the bend direction relative to the rolling grain and the "
                             "temper it applies to. NOT FOUND with a search trail is a "
                             "genuinely useful result here - it names a question for the shop.",
                    ),
                    Question(
                        "coupon_length", "Coupon length",
                        kind="number", units="mm", minimum=0, maximum=10000,
                        hint="Big enough to weld a representative length and still grip it; "
                             "small enough that you can afford several.",
                    ),
                    Question(
                        "coupon_width", "Coupon width",
                        kind="number", units="mm", minimum=0, maximum=10000,
                    ),
                    Question(
                        "coupon_count", "How many coupons in your matrix",
                        kind="integer", units="pieces", minimum=1, maximum=500,
                        hint="Enough to vary one thing at a time and repeat the interesting "
                             "cases. Step 4 is where you decide what varies.",
                    ),
                    Question(
                        "scrap_percent", "Scrap and setup allowance you are choosing",
                        kind="number", units="%", minimum=0, maximum=500,
                        hint="An allowance YOU chose, not a measured yield. Say what it covers "
                             "in 'assumptions' - trim, nesting, setup pieces, sectioned coupons.",
                    ),
                ),
                visual="coupon_plan.html",
            ),
            Step(
                "process", "3. Joint, access, filler, fixture, distortion",
                "Now the part you already know something about. Five questions, and "
                "they interact.\n\n"
                "JOINT AND ACCESS. Butt, lap, corner or edge - and can the torch "
                "physically reach it, at an angle you can hold, with the filler "
                "hand somewhere useful? A joint that is fine on a drawing and "
                "unreachable inside a 149 mm cylinder is a design problem, not a "
                "welding problem, and it is much cheaper to find now.\n\n"
                "PROCESS AND FILLER. For 6061-T6, trade guidance (Armao, The "
                "Welder, 2006 - guidance, not a specification) is that 5356 has "
                "roughly 50% higher shear strength, which matters for fillet and "
                "lap joints loaded in shear; 4043 is less crack-sensitive, is "
                "preferred for service above about 150 F, and anodises black while "
                "5356 stays silver. The point that matters most here: a 6061-T6 "
                "BUTT weld fails in the heat-affected zone whichever filler you "
                "use. The parent T6 properties are not the joint's properties. Any "
                "allowable for a welded joint has to be a welded allowable, from a "
                "design source, at the service temperature.\n\n"
                "FIXTURING AND DISTORTION. TWI Job Knowledge 33 names the modes: "
                "longitudinal and transverse shrinkage, angular distortion from "
                "uneven contraction through the thickness, bowing and dishing when "
                "the weld is off the neutral axis, buckling - which thin plate is "
                "especially prone to, and which is unstable, so a buckled panel can "
                "snap through and dish the other way - and twisting in box "
                "sections. Restraint reduces distortion but raises residual stress "
                "and, in a sensitive material, cracking risk. Predict which mode "
                "YOUR joint will show, then measure whether you were right. Being "
                "wrong here is a useful finding and worth writing down.",
                (
                    Question(
                        "joint_type",
                        "Joint type",
                        kind="choice",
                        choices=("butt", "lap", "corner", "edge", "fillet on a tee",
                                 "UNKNOWN - to be decided with the shop"),
                    ),
                    Question(
                        "joint_access",
                        "Describe torch and filler access, and any position you cannot reach",
                        hint="Include whether it is welded from one side or both, and what you "
                             "would have to do to reach the inside of a closed cylinder.",
                    ),
                    Question(
                        "process_filler",
                        "Proposed process and filler, with the evidence for the combination",
                        hint="Cite something. If your evidence is trade guidance rather than a "
                             "specification, say so and use basis: candidate. If it is your "
                             "own shop experience, that is real evidence - use basis: student "
                             "and describe the conditions.",
                    ),
                    Question(
                        "fixturing",
                        "How would you hold it, and what does that fixture cost you?",
                        hint="Chill bars, backing, clamps, tacks, weld sequence. Remember that "
                             "restraint trades distortion for residual stress.",
                    ),
                    Question(
                        "distortion_prediction",
                        "Which distortion mode do you predict, and in which direction?",
                        evidence=False,
                        hint="Commit to a prediction before you measure. Use the TWI list in "
                             "the reading. Being wrong is a result, not a failure.",
                    ),
                ),
                visual="coupon_plan.html",
            ),
            Step(
                "inspection", "4. A coupon matrix, and a plan for looking at it",
                "A pile of welded scrap is not evidence. A matrix is: vary ONE "
                "thing at a time, hold the rest fixed, write down what you held "
                "fixed, and repeat the interesting case at least once so you can "
                "tell a real effect from a bad day.\n\n"
                "Then decide, in advance, what you will measure and with what. "
                "Out-of-round with a bore gauge or a surface plate and height "
                "gauge. Angular distortion with a straight edge and feeler gauges. "
                "Bead profile and undercut visually against a stated acceptance "
                "description. Penetration by sectioning one coupon and etching it. "
                "Write the numbers down with the instrument and its resolution - "
                "'flat' is not a measurement and 'looks good' is not an "
                "inspection.\n\n"
                "Be precise about what a coupon is worth. AWS D17.1/D17.1M:2024 "
                "keeps three things separate: qualifying a welding PROCEDURE, "
                "qualifying a WELDER or operator, and PRODUCTION welding. A "
                "practice coupon made on the bench is none of those. It is process "
                "development: it tells you what happens, informs what a real "
                "procedure would have to control, and has no standing as "
                "qualification. Anyone who reads your coupon as approval has "
                "misread it, so say so on the record now.",
                (
                    Question(
                        "matrix_variable",
                        "What is the ONE thing your matrix varies?",
                        evidence=False,
                        hint="Heat input, travel speed, fixturing, weld sequence, tack spacing, "
                             "filler. One of them. Name what you hold fixed too.",
                    ),
                    Question(
                        "inspection_plan",
                        "What will you measure, with what instrument, and to what resolution?",
                        hint="Use /text. One line per measurement. Include how you would "
                             "record a coupon that fails - a bad coupon is data.",
                    ),
                    Question(
                        "coupon_status",
                        "What standing does a coupon from this matrix have?",
                        kind="choice",
                        choices=("practice/process-development coupon only - no qualification",
                                 "input toward a future qualified procedure, not the procedure",
                                 "I am not sure and will ask the welding authority"),
                        hint="There is no option here that makes a bench coupon a qualified "
                             "procedure or a pressure-rated part, because it is not one. Cite "
                             "AWS D17.1's separation of procedure, performance and production.",
                    ),
                ),
                visual="coupon_plan.html",
            ),
            Step(
                "tolerance", "5. Push the distortion back into the assembly",
                "This is the step that makes the coupon matter, and it is the one "
                "most often skipped.\n\n"
                "A reverse-flow engine assembles a liner inside a casing bore. "
                "config/limits.yaml requires a radial clearance of "
                "casing_fit_margin_min_m = 0.002 m - 2 mm - with the comment that "
                "zero clearance 'means the liner is touching the casing, which is "
                "not an assembly'. Every millimetre your fabrication gives away "
                "comes out of that 2 mm.\n\n"
                "So add it up, worst case: sheet thickness tolerance, rolled "
                "out-of-round, the seam pulling the diameter in or out, fit-up gap "
                "at the joint, and the bracket or flange positional tolerance. "
                "Worst case, not root-sum-square - RSS assumes independent, "
                "centred, random variation, and welding distortion is a systematic "
                "bias with a direction, not a random wobble.\n\n"
                "If the stack eats the clearance, you have found something real and "
                "cheap: either the process has to get tighter, or the nominal "
                "clearance has to grow, or a machining operation has to be added "
                "after welding. That is a design decision, owned by the structures "
                "lead, and you have just handed them the number it turns on.",
                (
                    Question(
                        "nominal_clearance",
                        "Nominal radial clearance your assembly starts with",
                        kind="number", units="mm", minimum=0, maximum=1000,
                        hint="2 mm is the current floor in config/limits.yaml. If your part "
                             "has a different nominal, say where it comes from.",
                    ),
                    Question(
                        "roundness_tol",
                        "Out-of-round you expect from rolling and forming (radial)",
                        kind="number", units="mm", minimum=0, maximum=1000,
                        hint="Estimate it if you must and use basis: hypothesis. This is "
                             "exactly the number the coupon exists to replace with a measurement.",
                    ),
                    Question(
                        "distortion_allow",
                        "Radial movement you expect from welding distortion",
                        kind="number", units="mm", minimum=0, maximum=1000,
                        hint="Direction matters but this stack uses magnitude. Note in "
                             "'assumptions' whether you expect the seam to pull the diameter "
                             "in or push it out.",
                    ),
                    Question(
                        "fitup_tol",
                        "Fit-up and assembly positional tolerance",
                        kind="number", units="mm", minimum=0, maximum=1000,
                        hint="Joint gap, bracket position, flange squareness - whatever else "
                             "moves the liner relative to the bore.",
                    ),
                ),
                visual="coupon_plan.html",
            ),
            Step(
                "shop", "6. What the shop can do, and what you need to ask it",
                "Two different things, and it is worth keeping them apart: what you "
                "KNOW the shop has, and what you need to ASK.\n\n"
                "Known equipment and confirmed access is evidence. Training and "
                "authorisation is separate from equipment - a machine you are not "
                "signed off on is not a machine you have. Old task cards are not "
                "proof of current access, and workspaces/combustion-systems/"
                "C2-fabrication.md already warns against relying on dates in them.\n\n"
                "Then write the questions. Good ones are specific enough to be "
                "answered in a sentence: 'What is the largest sheet the rolls will "
                "take at 1.5 mm, and what is the minimum diameter?' beats 'can you "
                "help with rolling?'\n\n"
                "Write them. Do not send them. Nothing in this lesson authorises "
                "contacting the shop, the welding authority or a supplier; the lead "
                "arranges that, and the Chief engineer owns supplier contact.",
                (
                    Question(
                        "shop_known",
                        "What equipment and access do you KNOW the team has?",
                        hint="Say how you know. 'The lead confirmed on <date>' is evidence; "
                             "'the card says so' may be out of date.",
                    ),
                    Question(
                        "training_status",
                        "What training or authorisation is needed, and who currently has it?",
                        hint="Use anonymous slots, never names. UNKNOWN is common and worth "
                             "recording - it is often the real schedule risk.",
                    ),
                    Question(
                        "shop_questions",
                        "Write the questions for the shop and the welding authority (do not send them)",
                        evidence=False, role="next_step",
                        hint="Use /text, one question per line, three to six of them. Specific "
                             "enough to answer in a sentence each.",
                    ),
                ),
            ),
            Step(
                "cost", "7. Cash and in-kind, on separate lines",
                "One rule, and docs/project/budget-cap.md states it plainly: count "
                "a donation once, against the line it actually replaces. The team "
                "already has free machine-shop access; that is not a new saving to "
                "subtract again. Atlas Copco's sponsorship is confirmed as a "
                "relationship, but its scope, value and delivery date are NOT "
                "FOUND, and nothing should be credited against it until the Chief "
                "engineer confirms what it covers.\n\n"
                "So this step records two different things in two different "
                "places. CASH is price plus shipping for a stated quantity in a "
                "stated currency - and only that. It excludes tax, duty, tooling, "
                "consumables and shop time, and the calculation below deliberately "
                "does not subtract anything donated. CONFIRMED IN-KIND is a "
                "separate note: what service or material, confirmed by whom, and "
                "when it arrives.\n\n"
                "Never write an unknown price as zero. UNKNOWN is a number the "
                "Chief engineer can work with; a false zero is not.\n\n"
                "One allocation request, through the Chief engineer, coordinated "
                "with the structures lead. Not a purchase. The relevant envelope is "
                "'Stand, safety, approved ground support and consumables' at $900, "
                "or 'Hot section, rotating parts, tooling and balancing' at $1,700 "
                "if your stock is for a hot part - say which you are asking "
                "against, because they are not interchangeable.",
                (
                    Question(
                        "stock_price",
                        "Stock subtotal for the quantity you sized above (cash only)",
                        kind="number", units="USD", minimum=0, maximum=1000000,
                        hint="One supplier, one currency, one quantity, with the date. Use "
                             "UNKNOWN rather than 0 if you do not have a price - a false zero "
                             "is worse than a gap.",
                    ),
                    Question(
                        "shipping_cost",
                        "Shipping for that same quote (cash only)",
                        kind="number", units="USD", minimum=0, maximum=1000000,
                        hint="UNKNOWN, not 0, if the quote does not say. Missing shipping is "
                             "missing, not free.",
                    ),
                    Question(
                        "inkind_scope",
                        "Confirmed in-kind coverage: what, confirmed by whom, arriving when",
                        hint="'Not confirmed' is the correct answer for anything nobody has "
                             "actually agreed to yet. Do NOT subtract it from the cash figure; "
                             "record it here so the Chief engineer can count it exactly once. "
                             "Keep supplier correspondence private - summary only.",
                    ),
                    Question(
                        "budget_envelope",
                        "Which spending envelope are you asking against?",
                        kind="choice",
                        choices=("Stand, safety, approved ground support and consumables ($900)",
                                 "Hot section, rotating parts, tooling and balancing ($1,700)",
                                 "Unallocated design and rework contingency ($750)",
                                 "UNKNOWN - to be settled with the Chief engineer"),
                        hint="Cite docs/project/budget-cap.md. Choosing an envelope is a "
                             "proposal to the Chief engineer, not an approval, and this lesson "
                             "authorises no spending at all.",
                    ),
                ),
            ),
            Step(
                "handoff", "8. The decisions somebody else owns",
                "Finish by naming what the team now has to decide. You are not "
                "deciding these, and that is the point: a good feasibility package "
                "makes other people's decisions cheap and obvious rather than "
                "making them for them.\n\n"
                "The structures lead owns the casing and liner design and the "
                "clearance. The shop and the welding authority own process "
                "capability, training and any weld procedure. Safety owns anything "
                "that runs, spins or holds pressure. The Chief engineer owns money "
                "and supplier contact. None of that changes because a lesson is "
                "complete.",
                (
                    Question(
                        "decisions_needed",
                        "List the decisions the team must make, and who owns each",
                        evidence=False, role="decision",
                        hint="Use /text, one per line, in the form 'decision - owner'. Three "
                             "to six. This is the most valuable output of the whole lesson.",
                    ),
                    Question(
                        "next_step",
                        "What is your next small step?",
                        evidence=False, role="next_step",
                        hint="One step, 30 minutes or less, that does not require spending, "
                             "shop entry or contacting anyone outside the team.",
                    ),
                ),
            ),
        ),
        calculations=(
            Calculation(
                "stock_area", "Sheet area to buy, including your scrap allowance",
                ("coupon_length", "coupon_width", "coupon_count", "scrap_percent"),
                lambda coupon_length, coupon_width, coupon_count, scrap_percent:
                    sm.coupon_stock_area_mm2(coupon_length, coupon_width,
                                             coupon_count, scrap_percent),
                units="mm^2",
                method="area = L * W * n * (1 + scrap/100), all in mm. Flat area only.",
                version="1",
                limitations="Flat area, no nesting layout, no allowance for standard sheet "
                            "sizes or minimum order quantity - you may have to buy a whole "
                            "sheet regardless. The scrap figure is an allowance you chose, "
                            "not a measured yield. This is not a quotation.",
            ),
            Calculation(
                "cash_cost", "CASH cost of the stock: price + shipping",
                ("stock_price", "shipping_cost"),
                lambda stock_price, shipping_cost: sm.cash_stock_cost_usd(
                    stock_price, shipping_cost),
                units="USD",
                method="cash = stock_price + shipping, same quote, same quantity, same currency.",
                version="1",
                limitations="Cash only. Excludes tax, duty, tooling, consumables, shop time and "
                            "any other line item. Confirmed in-kind coverage is deliberately "
                            "NOT subtracted here, so that a donation is counted exactly once, "
                            "by the Chief engineer, against the line it replaces. Not a "
                            "quotation, not a purchase and not an approval to spend.",
            ),
            Calculation(
                "clearance_left", "Radial clearance left after the worst-case stack",
                ("nominal_clearance", "roundness_tol", "distortion_allow", "fitup_tol"),
                lambda nominal_clearance, roundness_tol, distortion_allow, fitup_tol:
                    sm.radial_clearance_after_stack_mm(
                        nominal_clearance, roundness_tol, distortion_allow, fitup_tol),
                units="mm",
                method="clearance_left = nominal - (|roundness| + |distortion| + |fit-up|), "
                       "worst-case arithmetic stack in mm. Worst case rather than "
                       "root-sum-square, because welding distortion is a systematic bias "
                       "with a direction, not independent random variation.",
                version="1",
                limitations="A NEGATIVE result means interference: the parts do not go "
                            "together at worst case. It is reported as a negative number "
                            "rather than clipped to zero. Compare against "
                            "casing_fit_margin_min_m = 0.002 m in config/limits.yaml. Built "
                            "from tolerances you estimated; replacing those estimates with "
                            "measurements is what the coupon matrix is for. Not an assembly "
                            "release.",
            ),
        ),
    )


if __name__ == "__main__":
    raise SystemExit(run_lesson(build_lesson(), __file__))
