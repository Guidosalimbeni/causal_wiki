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
