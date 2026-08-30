"""What this company has already estimated with, and how it had to be tailored.

Deliberately not a textbook. IV, DiD, interrupted time series and the rest are
in the model's training data already, and restating them here would be the least
useful thing this wiki could hold. What is *not* anywhere else is the local
shape of them: which instrument survived contact with this business, which
window the seasonality forces, which cohort definition the billing system makes
possible, and what went wrong the last time someone tried.

So a method note is written after a question, not before one, and it accretes.
Kept apart from `wiki/experiments/`, which records a specific thing that was run
and what it found — a different claim with a different lifetime.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ..config import Config
from ..records import question as qmod
from . import frontmatter


@dataclass
class Method:
    id: str
    title: str
    aliases: list[str] = field(default_factory=list)
    path: Path | None = None

    @property
    def names(self) -> list[str]:
        return [self.id, *self.aliases]


def tokens(text: str) -> list[str]:
    """`backdoor.propensity_score_weighting` and `propensity-score weighting`
    have to land on the same note, so punctuation carries no meaning."""
    return re.findall(r"[a-z0-9]+", str(text).lower())


def _contains(haystack: list[str], needle: list[str]) -> bool:
    """Consecutive-run match, not substring: `iv` must be a word of its own,
    or every note would match every method that happens to contain the letters."""
    if not needle or len(needle) > len(haystack):
        return False
    return any(
        haystack[i : i + len(needle)] == needle
        for i in range(len(haystack) - len(needle) + 1)
    )


def load(cfg: Config) -> list[Method]:
    if not cfg.methods_dir.exists():
        return []
    out: list[Method] = []
    for path in sorted(cfg.methods_dir.rglob("*.md")):
        try:
            doc = frontmatter.load(path)
        except Exception:
            continue
        raw = doc.meta.get("aliases") or []
        aliases = [raw] if isinstance(raw, str) else [str(a) for a in raw]
        out.append(
            Method(
                id=str(doc.meta.get("id") or path.stem),
                title=str(doc.meta.get("label") or doc.meta.get("title") or path.stem),
                aliases=aliases,
                path=path,
            )
        )
    return out


def match(methods: list[Method], recorded: str) -> Method | None:
    """The note covering the `method:` string on a question record, if any."""
    if not recorded:
        return None
    words = tokens(recorded)
    best: tuple[int, Method] | None = None
    for method in methods:
        for name in method.names:
            needle = tokens(name)
            if _contains(words, needle) and (best is None or len(needle) > best[0]):
                best = (len(needle), method)
    return best[1] if best else None


@dataclass
class Use:
    """One question that reached for this note, and in which capacity."""

    question: "qmod.Question"
    role: str  # "estimated" | "design"

    @property
    def recorded(self) -> str:
        return (self.question.method if self.role == "estimated" else self.question.design) or ""


def usage(cfg: Config, notes: list[Method] | None = None) -> dict[str, list[Use]]:
    """Which questions each note covers, keyed by note id.

    A note is reached for in two ways and both count: as the estimator a
    question was answered with, and as the design a question proposed. Counting
    only the first would show a company's standing test design as unused right
    up until someone ran one.
    """
    notes = load(cfg) if notes is None else notes
    out: dict[str, list[Use]] = {}
    for q in qmod.iter_questions(cfg.questions):
        for role, recorded in (("estimated", q.method), ("design", q.design)):
            note = match(notes, recorded or "")
            if note:
                out.setdefault(note.id, []).append(Use(question=q, role=role))
    for uses in out.values():
        uses.sort(key=lambda u: u.question.id)
    return out


def unwritten(cfg: Config, notes: list[Method] | None = None) -> dict[str, list]:
    """Methods and designs on record with no note explaining the local shape."""
    notes = load(cfg) if notes is None else notes
    out: dict[str, list] = {}
    for q in qmod.iter_questions(cfg.questions):
        for recorded in (q.method, q.design):
            if recorded and not match(notes, recorded):
                out.setdefault(recorded, []).append(q)
    return out
