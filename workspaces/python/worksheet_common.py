"""Shared helpers for the CORE first-meeting Python worksheets.

This is teaching support, nothing else. The module deliberately:

  * uses nothing outside the Python standard library,
  * never imports the engine model in ``core/`` or ``modules/``,
  * never reads or writes project configuration,
  * never writes a file.

Nothing typed into a worksheet can change a design input. A worksheet prints
a block of text. A lead decides whether any of that text belongs in the shared
design record. See ``LEAD-REVIEW.md``.

Output is plain ASCII on purpose, so it survives every terminal, code page and
text editor the team is likely to use, and so redirecting output to a file
never fails with an encoding error.
"""

import sys
from dataclasses import dataclass
from textwrap import fill

WIDTH = 78

# ---------------------------------------------------------------------------
# Two different kinds of "I do not have a number"
# ---------------------------------------------------------------------------
# UNKNOWN   = you have not filled this in yet.
# NOT_FOUND = you looked, and the information genuinely is not available.
#
# NOT_FOUND is a real result. Write it with confidence. Half of engineering is
# finding out what nobody has written down yet. What is NOT allowed is
# inventing a plausible-looking number to fill the gap.
UNKNOWN = "UNKNOWN"
NOT_FOUND = "NOT FOUND"

# ---------------------------------------------------------------------------
# Where a number came from. Keep these apart; they are not interchangeable.
# ---------------------------------------------------------------------------
EXAMPLE = "EXAMPLE"        # invented for this worksheet to show the arithmetic
CANDIDATE = "CANDIDATE"    # a DP-2 proposal under review; not approved
REPO_CHECK = "REPO CHECK"  # reproduced by docs/project/checks/dp2_screen.py
SOURCE = "SOURCED"         # you found it in a document you can cite
MEASURED = "MEASURED"      # somebody actually measured it
STUDENT = "YOUR ENTRY"     # whatever you typed in the answers block

_BASIS_HELP = {
    EXAMPLE: "illustration only - never copy into a CORE document",
    CANDIDATE: "DP-2 proposal, under review, not an approved value",
    REPO_CHECK: "reproduced by this repository's own screening script",
    SOURCE: "found in a citable source",
    MEASURED: "actually measured",
    STUDENT: "entered by you in this worksheet",
}


@dataclass
class Answer:
    """One thing you are asked to find out, with its paperwork attached."""

    value: object = UNKNOWN
    units: str = ""
    source: str = UNKNOWN
    uncertainty: str = UNKNOWN
    basis: str = STUDENT
    note: str = ""


def answer(value=UNKNOWN, units="", source=UNKNOWN, uncertainty=UNKNOWN,
           basis=STUDENT, note=""):
    """Record one finding together with its units, source and uncertainty.

    Keeping those four things in the same place is the whole point. A number
    on its own is not evidence.
    """
    return Answer(value=value, units=units, source=source,
                  uncertainty=uncertainty, basis=basis, note=note)


# ---------------------------------------------------------------------------
# Reading what the student typed, without ever crashing on it
# ---------------------------------------------------------------------------

_BLANK_WORDS = {"", "UNKNOWN", "NOT FOUND", "NOTFOUND", "TBD", "TODO", "?",
                "...", "N/A", "NA", "NONE", "FILL ME IN"}


def raw(value):
    """Unwrap an Answer, or pass a plain value straight through."""
    return value.value if isinstance(value, Answer) else value


def has_value(value):
    """True when there is something real here that we could compute with."""
    value = raw(value)
    if value is None:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        return value.strip().upper() not in _BLANK_WORDS
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) > 0
    return True


def is_not_found(value):
    """True when the student explicitly recorded NOT FOUND."""
    value = raw(value)
    return isinstance(value, str) and value.strip().upper() in {"NOT FOUND", "NOTFOUND"}


def is_recorded(value):
    """True when the student made a decision: a real value, or NOT FOUND."""
    return has_value(value) or is_not_found(value)


def as_number(value):
    """Return a float, or None. Never raises."""
    value = raw(value)
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip().replace(",", "").replace("_", "")
        try:
            return float(text)
        except ValueError:
            return None
    return None


def fmt_num(value, digits=6):
    """Format a number for reading, without pretending to false precision."""
    if value is None:
        return UNKNOWN
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return "not a usable number"
        if value == int(value) and abs(value) < 1e15:
            return str(int(value))
        text = "{:.{d}g}".format(value, d=digits)
        if "e" in text and 1e-4 <= abs(value) < 1e12:
            text = "{:.{d}f}".format(value, d=digits).rstrip("0").rstrip(".")
        return text
    return str(value)


# ---------------------------------------------------------------------------
# The worksheet itself
# ---------------------------------------------------------------------------

class Worksheet:
    """Prints a worksheet, collects the answers, and reports what is missing.

    A worksheet never decides whether an answer is right. It only reports
    whether an answer is *present*, and shows the arithmetic it was able to
    do. The lead does the judging.
    """

    def __init__(self, code, title, card, review_role, minutes="30 to 45"):
        self.code = code
        self.title = title
        self.card = card
        self.review_role = review_role
        self.minutes = minutes
        self.mode = "full"
        self._slots = []          # (label, value) pairs shown in the done check
        self._recorded = []       # (label, Answer) pairs shown in the report
        self._computed = []       # (label, text) results of ws.compute
        self._submission = {}
        if "--form" in sys.argv:
            self.mode = "form"
        if "--help" in sys.argv or "-h" in sys.argv:
            self.mode = "help"

    # -- plumbing ----------------------------------------------------------

    @property
    def _quiet(self):
        return self.mode != "full"

    def _out(self, text=""):
        if not self._quiet:
            print(text)

    # -- layout ------------------------------------------------------------

    def header(self, safety_line="Desk work only today. No hardware, no fuel, "
                                 "no rotor operation, no shop machinery."):
        if self.mode == "help":
            self._print_help()
            raise SystemExit(0)
        self._out("=" * WIDTH)
        self._out(" CORE first-meeting Python worksheet")
        self._out(" {0} - {1}".format(self.code, self.title))
        self._out("=" * WIDTH)
        self._out(" Task card   : {0}".format(self.card))
        self._out(" Review role : {0}".format(self.review_role))
        self._out(" Time        : {0} minutes".format(self.minutes))
        self._out(" Today       : " + fill(safety_line, WIDTH - 15,
                                           subsequent_indent=" " * 15))
        self._out("")
        self._out(" The task card is the authority on what is in and out of scope.")
        self._out(" This worksheet only teaches the topic and collects your answers.")
        self._out("")

    def _print_help(self):
        print("{0} - {1}".format(self.code, self.title))
        print("")
        print("  python <this file>            read the lesson and see your progress")
        print("  python <this file> --form     print a blank form you can fill in on paper")
        print("  python <this file> --help     this message")
        print("")
        print("Edit the block marked YOUR ANSWERS near the top of the file, save,")
        print("then run it again. See workspaces/python/HOW-TO-RUN.md.")

    def heading(self, text):
        self._out("")
        line = "-- " + text.upper() + " "
        self._out(line + "-" * max(0, WIDTH - len(line)))
        self._out("")

    def say(self, text, indent=""):
        self._out(fill(" ".join(text.split()), WIDTH,
                       initial_indent=indent, subsequent_indent=indent))
        self._out("")

    def bullets(self, items, marker="  * "):
        pad = " " * len(marker)
        for item in items:
            self._out(fill(" ".join(item.split()), WIDTH,
                           initial_indent=marker, subsequent_indent=pad))
        self._out("")

    def terms(self, pairs):
        """A few words, in plain language, that this task needs."""
        for word, meaning in pairs:
            self._out("  " + word)
            self._out(fill(" ".join(meaning.split()), WIDTH,
                           initial_indent="      ", subsequent_indent="      "))
            self._out("")

    def table(self, headers, rows):
        cols = len(headers)
        widths = [len(str(h)) for h in headers]
        for row in rows:
            for i in range(cols):
                widths[i] = max(widths[i], len(str(row[i])))
        total = sum(widths) + 3 * (cols - 1) + 2
        if total > WIDTH:                      # shrink the widest column
            widest = widths.index(max(widths))
            widths[widest] = max(8, widths[widest] - (total - WIDTH))

        def line(cells):
            parts = []
            for i in range(cols):
                parts.append(str(cells[i])[:widths[i]].ljust(widths[i]))
            return "  " + "   ".join(parts).rstrip()

        self._out(line(headers))
        self._out("  " + "   ".join("-" * w for w in widths))
        for row in rows:
            self._out(line(row))
        self._out("")

    def blank(self):
        self._out("")

    def legend(self, kinds=(CANDIDATE, REPO_CHECK, EXAMPLE)):
        """Explain, once, how to read the tags in front of every given value."""
        self._out("  How to read the tag in front of a number:")
        for kind in kinds:
            self._out("    {0:<12}{1}".format(kind, _BASIS_HELP.get(kind, "")))
        self._out("")

    def given(self, label, value, units="", basis=CANDIDATE, source=""):
        """Show a value the project already has, with where it came from.

        Illustrative examples, DP-2 candidates and reproduced repository
        results are printed differently on purpose. They are not the same kind
        of number and must not be mixed in your notes.
        """
        shown = (fmt_num(value, 6) + " " + units).strip()
        label = label if len(label) <= 44 else label[:41] + "..."
        dots = "." * max(2, 48 - len(label))
        self._out("  {0:<12}{1} {2} {3}".format(basis, label, dots, shown))
        if source:
            self._out(fill(source, WIDTH, initial_indent=" " * 14,
                           subsequent_indent=" " * 14))

    def example(self, lines):
        """A worked example. Every number in here is illustrative."""
        self._out("  [" + EXAMPLE + "] worked example - illustration only")
        self._out("  " + "-" * (WIDTH - 4))
        for text in lines:
            self._out(("    " + text).rstrip())
        self._out("  " + "-" * (WIDTH - 4))
        self._out("")

    # -- calculation -------------------------------------------------------

    def compute(self, label, function, inputs, units="", digits=6, comment=""):
        """Run ``function`` only when every input has a real value.

        ``inputs`` is an ordered dict of plain-English name -> value. The
        values are passed to ``function`` positionally, in that order, so the
        names can read like English instead of like variable names.

        When something is missing the worksheet says exactly what, and returns
        None. It never substitutes a default and never prints a number that
        was not computed from your own entries.
        """
        numbers = {}
        missing = []
        unreadable = []
        for name, value in inputs.items():
            if not has_value(value):
                missing.append(name)
                continue
            number = as_number(value)
            if number is None:
                unreadable.append(name)
            else:
                numbers[name] = number

        if missing or unreadable:
            self._computed.append((label, "not computed"))
            self._out("  {0}: not computed yet.".format(label))
            if missing:
                self._out(fill("still needed: " + ", ".join(missing), WIDTH,
                               initial_indent="      ", subsequent_indent="      "))
            if unreadable:
                self._out(fill("could not be read as a number (check for stray "
                               "text or units inside the value): "
                               + ", ".join(unreadable), WIDTH,
                               initial_indent="      ", subsequent_indent="      "))
            self._out("")
            return None

        try:
            result = function(*[numbers[name] for name in inputs])
        except ZeroDivisionError:
            self._computed.append((label, "not computed"))
            self._out("  {0}: not computed - one of your entries divides by "
                      "zero.".format(label))
            self._out("")
            return None
        except (ValueError, OverflowError, TypeError) as exc:
            self._computed.append((label, "not computed"))
            self._out("  {0}: not computed - {1}".format(label, exc))
            self._out("")
            return None

        shown = "{0} {1}".format(fmt_num(result, digits), units).strip()
        self._computed.append((label, shown))
        self._out("  {0} = {1}".format(label, shown))
        if numbers:
            detail = ", ".join("{0} {1}".format(k, fmt_num(v, digits))
                               for k, v in numbers.items())
            self._out(fill("from your entries: " + detail, WIDTH,
                           initial_indent="      ", subsequent_indent="      "))
        if comment:
            self._out(fill(comment, WIDTH, initial_indent="      ",
                           subsequent_indent="      "))
        self._out("")
        return result

    # -- collecting answers ------------------------------------------------

    def record(self, label, value):
        """Register one answer so it appears in the paste-ready report."""
        if not isinstance(value, Answer):
            value = answer(value=value)
        self._recorded.append((label, value))
        return value

    def submission(self, date=UNKNOWN, learned=UNKNOWN, unknown=UNKNOWN,
                   question=UNKNOWN, next_step=UNKNOWN):
        """The five fields every CORE task card asks for."""
        self._submission = {
            "date": date,
            "learned": learned,
            "unknown": unknown,
            "question": question,
            "next_step": next_step,
        }

    def done_when(self, checks):
        """``checks`` is a list of (plain-English requirement, value)."""
        self._slots = list(checks)

    # -- finishing ---------------------------------------------------------

    def _status_lines(self):
        lines = []
        done = 0
        for label, value in self._slots:
            if is_not_found(value):
                mark, note = "x", "recorded as NOT FOUND (a valid answer)"
                done += 1
            elif has_value(value):
                mark, note = "x", "recorded"
                done += 1
            else:
                mark, note = " ", "still blank"
            dots = "." * max(3, 52 - len(label))
            lines.append("  [{0}] {1} {2} {3}".format(mark, label, dots, note))
        return lines, done

    def _report_text(self):
        sub = self._submission
        out = []
        out.append("- Date: {0}".format(_field(sub.get("date"))))
        out.append("- Status: {0}".format(self._status_word()))
        out.append("- Source / file / revision: {0}".format(self._sources_text()))
        out.append("- What I learned (three sentences or a labeled sketch):")
        for line in _as_lines(sub.get("learned")):
            out.append("    {0}".format(line))
        out.append("- Quantity / units / assumption, if applicable:")
        if self._recorded:
            for label, ans in self._recorded:
                out.extend(_wrapped_item(_answer_line(label, ans)))
        else:
            out.append("    (this task records findings and sketches, not a "
                       "measured quantity)")
        for label, text in self._computed:
            if text == "not computed":
                continue
            out.extend(_wrapped_item(
                "{0} = {1} | basis: worksheet arithmetic on the entries "
                "above".format(label, text)))
        out.append("- What is still unknown: {0}".format(_field(sub.get("unknown"))))
        out.append("- Question for the review role: {0}".format(_field(sub.get("question"))))
        out.append("- Next small step agreed with the lead: {0}".format(
            _field(sub.get("next_step"))))
        out.append("- Review outcome and date: Not reviewed")
        out.append("- Worksheet: {0} ({1})".format(_script_name(), self.code))
        return out

    def _status_word(self):
        _, done = self._status_lines()
        total = len(self._slots)
        if total == 0:
            return "Not started"
        if done == 0:
            return "Not started"
        if done < total:
            return "In progress ({0} of {1} recorded)".format(done, total)
        return "Ready for lead review ({0} of {0} recorded)".format(total)

    def _sources_text(self):
        sources = []
        for _, ans in self._recorded:
            if is_recorded(ans.source) and ans.source not in sources:
                sources.append(str(raw(ans.source)))
        return "; ".join(sources) if sources else NOT_FOUND

    def _print_form(self):
        print("{0} - {1}".format(self.code, self.title))
        print("Blank form. Fill this in on paper or in any text box, then give")
        print("it to your lead or paste it into the first-meeting finding issue.")
        print("")
        print("Task code: {0}".format(self.code))
        print("Date: ______________________")
        print("")
        print("What this worksheet asks you to record:")
        for label, _ in self._slots:
            print("")
            print("  {0}".format(label))
            print("    value   : ____________________  units: ____________")
            print("    source  : ______________________________________________")
            print("    how sure: ______________________________________________")
        print("")
        print("  Three sentences on what you learned:")
        for _ in range(3):
            print("    ______________________________________________________")
        print("")
        print("  What is still unknown:")
        print("    ______________________________________________________")
        print("")
        print("  One question for the {0}:".format(self.review_role))
        print("    ______________________________________________________")
        print("")
        print("  Next small step, agreed with the lead:")
        print("    ______________________________________________________")
        print("")
        print("Writing NOT FOUND is a real answer. Inventing a number is not.")

    def finish(self):
        if self.mode == "form":
            self._print_form()
            return
        self.heading("where you are")
        lines, done = self._status_lines()
        for line in lines:
            self._out(line)
        self._out("")
        total = len(self._slots)
        if total:
            self._out("  {0} of {1} recorded. {2}".format(
                done, total,
                "Done for today." if done == total
                else "Fill in the rest, save, and run this again."))
        self._out("")

        self.heading("paste this into your card or your finding issue")
        self.say("Copy everything between the two lines. Replace the Findings "
                 "section of {0}, or paste it into the first-meeting finding "
                 "issue form. Your lead reviews it before anything here "
                 "becomes a project value.".format(self.card))
        self._out("  " + "-" * (WIDTH - 4))
        for line in self._report_text():
            self._out("  " + line)
        self._out("  " + "-" * (WIDTH - 4))
        self._out("")
        self.say("This worksheet changed nothing. It did not import the engine "
                 "model, did not read or write config/, and wrote no files. "
                 "A filled worksheet is learning evidence, not an approved "
                 "engineering result and not hardware authorisation.")
        self._out("  How to save and submit this: workspaces/python/HOW-TO-RUN.md")
        self._out("")


# ---------------------------------------------------------------------------
# small private helpers
# ---------------------------------------------------------------------------

def _wrapped_item(text, indent="    ", hang="      "):
    return fill(" ".join(text.split()), WIDTH - 4, initial_indent=indent,
                subsequent_indent=hang).split("\n")


def _script_name():
    try:
        import os
        return os.path.basename(sys.argv[0]) or "worksheet.py"
    except Exception:                                   # pragma: no cover
        return "worksheet.py"


def _field(value):
    if is_not_found(value):
        return NOT_FOUND
    if not has_value(value):
        return "NOT RECORDED"
    return str(raw(value))


def _as_lines(value):
    if isinstance(value, (list, tuple)):
        items = [str(v) for v in value if has_value(v)]
        return items if items else ["NOT RECORDED"]
    return [_field(value)]


def _answer_line(label, ans):
    value = ans.value
    if is_not_found(value):
        shown = NOT_FOUND
    elif not has_value(value):
        shown = "NOT RECORDED"
    else:
        shown = "{0} {1}".format(fmt_num(value), ans.units).strip()
    parts = ["{0} = {1}".format(label, shown)]
    parts.append("basis: {0}".format(ans.basis))
    parts.append("source: {0}".format(_field(ans.source)))
    parts.append("how sure: {0}".format(_field(ans.uncertainty)))
    if ans.note:
        parts.append(ans.note)
    return " | ".join(parts)
