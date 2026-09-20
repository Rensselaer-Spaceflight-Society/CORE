"""Version 1 lesson and evidence contract. Standard library only."""

from dataclasses import dataclass, field
import math
import re
from typing import Callable

SCHEMA_VERSION = 1
BASES = ("example", "candidate", "sourced", "measured", "hypothesis", "student")
ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
SLOT_RE = re.compile(r"P[0-9]{2,4}\Z")


def identifier(value):
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise ValueError("Use a short ID containing only letters, numbers, - or _.")
    return value


@dataclass(frozen=True)
class Question:
    id: str
    prompt: str
    kind: str = "text"  # text, number, integer, choice, boolean
    units: str = ""
    choices: tuple = ()
    minimum: float | None = None
    maximum: float | None = None
    required: bool = True
    evidence: bool = True
    hint: str = ""
    role: str = "finding"  # finding, decision, next_step
    comparison_key: str = ""  # only for the same physical quantity/part/conditions


@dataclass(frozen=True)
class Step:
    id: str
    title: str
    teaching: str
    questions: tuple[Question, ...]
    visual: str = ""  # path relative to the lesson's directory; optional


@dataclass(frozen=True)
class Calculation:
    id: str
    title: str
    inputs: tuple[str, ...]
    function: Callable = field(repr=False)
    units: str = ""
    method: str = ""
    version: str = "1"
    limitations: str = ""


@dataclass(frozen=True)
class Lesson:
    id: str
    version: str
    title: str
    review_role: str
    steps: tuple[Step, ...]
    prerequisites: tuple[str, ...] = ()
    minutes: str = "30-45"
    sources: tuple[str, ...] = ()
    calculations: tuple[Calculation, ...] = ()


def questions(lesson):
    return [q for step in lesson.steps for q in step.questions]


def validate_lesson(lesson):
    identifier(lesson.id)
    if not lesson.version or not lesson.title or not lesson.review_role:
        raise ValueError("Lesson needs a version, title and reviewer role.")
    qs = questions(lesson)
    if not qs or len({q.id for q in qs}) != len(qs):
        raise ValueError("Lesson needs questions with unique IDs.")
    if len({s.id for s in lesson.steps}) != len(lesson.steps):
        raise ValueError("Step IDs must be unique.")
    for step in lesson.steps:
        identifier(step.id)
        if not step.questions:
            raise ValueError("Each step needs at least one question.")
    for q in qs:
        identifier(q.id)
        if q.kind not in ("text", "number", "integer", "choice", "boolean"):
            raise ValueError("Unknown question type: " + q.kind)
        if q.kind == "choice" and not q.choices:
            raise ValueError("Choice question needs options.")
        if q.role not in ("finding", "decision", "next_step"):
            raise ValueError("Unknown question role.")
        for bound in (q.minimum, q.maximum):
            if bound is not None and (isinstance(bound, bool) or not math.isfinite(bound)):
                raise ValueError("Question bounds must be finite numbers.")
        if q.minimum is not None and q.maximum is not None and q.minimum > q.maximum:
            raise ValueError("Question minimum exceeds maximum.")
    ids = {q.id for q in qs}
    calc_ids = set()
    for calc in lesson.calculations:
        identifier(calc.id)
        if calc.id in calc_ids or not calc.inputs or not set(calc.inputs) <= ids:
            raise ValueError("Calculation IDs/inputs are invalid.")
        if not calc.method or not callable(calc.function):
            raise ValueError("Calculation needs a method and callable function.")
        calc_ids.add(calc.id)
    return lesson


def parse_value(q, value):
    if q.kind == "text":
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Please enter some text, or use /skip.")
        return value.strip()
    if q.kind == "choice":
        if value not in q.choices:
            raise ValueError("Choose: " + ", ".join(q.choices))
        return value
    if q.kind == "boolean":
        if isinstance(value, bool):
            return value
        if str(value).lower() in ("yes", "true", "y"):
            return True
        if str(value).lower() in ("no", "false", "n"):
            return False
        raise ValueError("Enter yes or no.")
    if isinstance(value, bool):
        raise ValueError("Enter a number, not yes/no.")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("Enter only the number, in the units shown (no commas).") from None
    if not math.isfinite(number):
        raise ValueError("The number must be finite; NaN and infinity are not evidence.")
    if q.kind == "integer" and not number.is_integer():
        raise ValueError("Enter a whole number.")
    if q.minimum is not None and number < q.minimum:
        raise ValueError(f"Use a value at least {q.minimum} {q.units}.")
    if q.maximum is not None and number > q.maximum:
        raise ValueError(f"Use a value at most {q.maximum} {q.units}.")
    return int(number) if q.kind == "integer" else number


def make_answer(q, entry, timestamp):
    if not isinstance(entry, dict):
        raise ValueError("Each answer must be an object with a value/status and evidence.")
    status = entry.get("status", "answered")
    if status not in ("answered", "unknown", "not_found"):
        raise ValueError("Answer status must be answered, unknown or not_found.")
    basis = entry.get("basis", "student")
    if basis not in BASES:
        raise ValueError("Unknown evidence basis.")
    fields = {}
    for key in ("source", "source_revision", "assumptions", "uncertainty", "reason"):
        value = entry.get(key, "")
        if not isinstance(value, str):
            raise ValueError(key + " must be text.")
        fields[key] = value.strip()
    if status == "not_found" and not fields["reason"]:
        raise ValueError("NOT FOUND needs a search trail: where you looked and what is missing.")
    value = parse_value(q, entry.get("value")) if status == "answered" else None
    if status == "answered" and q.evidence and (not fields["source"] or not fields["uncertainty"]):
        raise ValueError("Record a source and uncertainty/limits, or use UNKNOWN/NOT FOUND.")
    return dict(question_id=q.id, prompt=q.prompt, response_type=q.kind, role=q.role,
                comparison_key=q.comparison_key, value=value, units=q.units,
                status=status, basis=basis, edited_at=timestamp, **fields)


def completion(lesson, answers):
    missing = [q.id for q in questions(lesson) if q.required and
               answers.get(q.id, {}).get("status") not in ("answered", "not_found")]
    return ("in_progress" if missing else "ready_for_review"), missing


def calculate(lesson, answers):
    results = []
    for calc in lesson.calculations:
        inputs = {key: answers.get(key) for key in calc.inputs}
        result = dict(id=calc.id, title=calc.title, method=calc.method,
                      method_version=calc.version, units=calc.units,
                      limitations=calc.limitations, inputs=inputs,
                      basis="computed", status="missing_inputs", value=None)
        if all(a and a["status"] == "answered" for a in inputs.values()):
            try:
                value = calc.function(**{k: a["value"] for k, a in inputs.items()})
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError("Result is not a finite number.")
                result.update(value=value, status="computed")
            except (ArithmeticError, ValueError, TypeError) as exc:
                result.update(status="invalid_inputs", error=str(exc))
        results.append(result)
    return results
