"""Ranking the wiki for one question.

`cb context` exists so Claude need not grep blind. Printing *everything* stops
serving that the moment a project has been used for a few months: with several
analysts asking a question a day, an unfiltered pack is three hundred lines of
prior questions, and the three that bear on this one are buried in it.

So priors are ranked by what actually makes an earlier question relevant — it
touched the same variables, or their neighbours, or the same named graph — and
the tail is counted rather than printed. Nothing is hidden silently: the count
and the command that would show it are always on the page.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import Config
from .index import queries
from .records import question as qmod
from .records.question import Question
from .wiki import graph as wikigraph

# What makes a prior question worth reading, most telling first.
SHARED_NODE = 5
NEIGHBOUR_NODE = 2
SAME_GRAPH = 2
TEXT_MATCH = 2
HAS_FINDING = 1


@dataclass
class Ranked:
    question: Question
    score: int = 0
    why: list[str] = field(default_factory=list)

    @property
    def reason(self) -> str:
        return "; ".join(self.why)


def _neighbours(wiki: wikigraph.Wiki, nodes: set[str]) -> set[str]:
    """Nodes one causal hop away — a prior about a parent of this treatment is
    usually about the same confounding."""
    g = wiki.causal()
    out: set[str] = set()
    for node in nodes:
        if node in g:
            out |= set(g.predecessors(node)) | set(g.successors(node))
    return out - nodes


def _text_matches(cfg: Config, q: Question, limit: int = 20) -> set[str]:
    """Question ids whose text or interview reads like this one. Best effort:
    the index is derived, and may not have been built yet."""
    try:
        rows = queries.find(cfg, q.question, limit=limit)
    except Exception:
        return set()
    return {ref for kind, ref, _, _ in rows if kind in ("question", "interview")}


def rank_priors(cfg: Config, q: Question, wiki: wikigraph.Wiki | None = None) -> list[Ranked]:
    """Every prior question, most relevant first, recency breaking ties."""
    priors = [p for p in qmod.iter_questions(cfg.questions) if p.id != q.id]
    if not priors:
        return []

    own = q.nodes
    near = _neighbours(wiki, own) if (wiki and own) else set()
    matched = _text_matches(cfg, q)

    ranked: list[Ranked] = []
    for p in priors:
        r = Ranked(question=p)
        shared = own & p.nodes
        if shared:
            r.score += SHARED_NODE * len(shared)
            r.why.append(f"shares {', '.join(sorted(shared))}")
        touching = near & p.nodes
        if touching:
            r.score += NEIGHBOUR_NODE * len(touching)
            r.why.append(f"one hop from {', '.join(sorted(touching))}")
        if q.graph and p.graph == q.graph:
            r.score += SAME_GRAPH
            r.why.append(f"same graph {q.graph}")
        if p.id in matched:
            r.score += TEXT_MATCH
            r.why.append("wording matches")
        if p.finding or p.verdict:
            r.score += HAS_FINDING
        ranked.append(r)

    ranked.sort(key=lambda r: r.question.last_activity, reverse=True)
    ranked.sort(key=lambda r: r.score, reverse=True)  # stable: recency survives ties
    return ranked


# -- has this been asked before? ---------------------------------------------

# Words that carry no subject matter. Deliberately small: over-stripping makes
# unrelated questions look alike, which is worse than missing a duplicate.
STOPWORDS = {
    "a", "an", "and", "any", "are", "as", "at", "be", "by", "do", "does", "did", "for",
    "from", "has", "have", "how", "if", "in", "into", "is", "it", "its", "much", "of",
    "on", "or", "our", "that", "the", "their", "there", "this", "to", "was", "we",
    "were", "what", "when", "which", "who", "why", "with", "you", "your",
}

# Two questions overlapping this much in content words are the same question
# asked twice, near enough to be worth a look before the work starts again.
DUPLICATE_AT = 0.5


def content_words(text: str) -> set[str]:
    import re

    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS}


def similar_questions(
    cfg: Config, text: str, threshold: float = DUPLICATE_AT, limit: int = 3
) -> list[tuple[Question, float]]:
    """Questions already on record that read like this one.

    Deliberately independent of the DuckDB index: `cb ask` runs at stage two,
    often before anyone has rebuilt it, and a stale index is exactly when a
    duplicate slips through.
    """
    words = content_words(text)
    if not words:
        return []
    scored: list[tuple[Question, float]] = []
    for p in qmod.iter_questions(cfg.questions):
        other = content_words(p.question)
        if not other:
            continue
        overlap = len(words & other) / len(words | other)
        if overlap >= threshold:
            scored.append((p, overlap))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:limit]
