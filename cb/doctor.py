"""Validation.

A cycle, a contradictory edge, or an arithmetic edge mistyped as causal
silently corrupts every verdict downstream and is invisible when broken. The
checks are cheap; not having them is what lets Claude write a graph, read it
back next session as fact, and teach itself its own guesses.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import networkx as nx

from .config import Config
from .records import question as qmod
from .wiki import frontmatter, graph as wikigraph
from .wiki.nodes import NodeError


@dataclass
class Finding:
    level: str  # "error" | "warn"
    check: str
    message: str

    def __str__(self) -> str:
        icon = "✗" if self.level == "error" else "!"
        return f"{icon} [{self.check}] {self.message}"


def check(cfg: Config) -> list[Finding]:
    out: list[Finding] = []
    out += _check_scaffold(cfg)
    out += _check_graph(cfg)
    out += _check_questions(cfg)
    out += _check_tables(cfg)
    return out


def _check_scaffold(cfg: Config) -> list[Finding]:
    """The standing context is markdown, so its absence is silent.

    A project with the CLI but no CLAUDE.md still runs every command and still
    answers — just without the context that makes it causal work rather than a
    query tool. Nothing else would ever report that. `skills/` is deliberately
    not checked: it may legitimately live a level up, shared across projects.
    """
    out: list[Finding] = []
    if not (cfg.root / "CLAUDE.md").exists():
        out.append(
            Finding(
                "warn",
                "no-standing-context",
                "no CLAUDE.md — Claude Code has nothing telling it this is a causal "
                "wiki. `cb sync` writes the shipped one back.",
            )
        )
    return out


def _check_graph(cfg: Config) -> list[Finding]:
    if not cfg.graph_dir.exists():
        return [Finding("warn", "graph", f"no graph directory at {cfg.graph_dir}")]

    try:
        wiki = wikigraph.load(cfg.graph_dir)
    except (NodeError, frontmatter.FrontmatterError) as exc:
        return [Finding("error", "parse", str(exc))]

    out: list[Finding] = []

    for edge in wiki.dangling:
        missing = edge.source if edge.source not in wiki.nodes else edge.target
        out.append(
            Finding(
                "error",
                "dangling-link",
                f"{edge.source} -> {edge.target} references '{missing}', which has no node file "
                f"(declared in {edge.declared_in})",
            )
        )

    for conflict in wiki.conflicts:
        out.append(Finding("error", "contradictory-edge", str(conflict)))

    causal, arithmetic = wiki.causal(), wiki.arithmetic()

    # The mistype that would let an accounting identity be certified as a finding.
    both = set(causal.edges()) & set(arithmetic.edges())
    for s, t in sorted(both):
        out.append(
            Finding(
                "error",
                "edge-kind-clash",
                f"{s} -> {t} is declared as both causal and arithmetic. An identity is "
                f"exactly true and carries no causal content; pick one.",
            )
        )

    for name, g in (("causal", causal), ("arithmetic", arithmetic)):
        if not nx.is_directed_acyclic_graph(g):
            cycle = nx.find_cycle(g)
            pretty = " -> ".join(a for a, _ in cycle) + f" -> {cycle[-1][1]}"
            out.append(
                Finding(
                    "error",
                    f"{name}-cycle",
                    f"cycle in the {name} graph: {pretty}. Identification is undefined here.",
                )
            )

    for node in wiki.nodes.values():
        if not node.graphs:
            out.append(
                Finding("warn", "ungrouped-node", f"{node.id} belongs to no named graph")
            )
        if not node.observed and not str(node.meta.get("source", "")).strip():
            out.append(
                Finding(
                    "warn",
                    "unsourced-latent",
                    f"{node.id} is marked unobserved but records no source — a refusal will "
                    f"name it, so it should say where the claim came from",
                )
            )

    unconfirmed = [e for e in wiki.edges.values() if e.kind == "causal" and not e.confirmed]
    for edge in unconfirmed:
        out.append(
            Finding(
                "warn",
                "unconfirmed-edge",
                f"{edge.source} -> {edge.target} is unconfirmed; verdicts resting on it will "
                f"be marked provisional",
            )
        )
    return out


def _check_questions(cfg: Config) -> list[Finding]:
    out: list[Finding] = []
    if not cfg.questions.exists():
        return out
    seen: dict[str, Path] = {}
    for directory in sorted(cfg.questions.iterdir()):
        if not directory.is_dir() or not (directory / "question.md").exists():
            continue
        try:
            q = qmod.load(directory)
        except Exception as exc:
            out.append(Finding("error", "question", f"{directory.name}: {exc}"))
            continue
        # Ids are allocated as max+1 of what is on disk, so two analysts working
        # on two branches both get the same one and the collision only appears
        # at the merge — by which time the id is in file paths and cross
        # references. Cheap to detect, unpleasant to unpick later.
        if q.id in seen:
            out.append(
                Finding(
                    "error",
                    "duplicate-question-id",
                    f"{q.id} is used by both {seen[q.id].name} and {directory.name}. "
                    f"Renumber one — every reference to it is ambiguous until you do.",
                )
            )
        else:
            seen[q.id] = directory
        if q.status is qmod.Status.ABANDONED and not (q.abandoned_reason or "").strip():
            out.append(
                Finding("error", "abandoned-without-reason", f"{q.id}: no abandoned_reason")
            )
        if q.verdict and q.verdict != "IDENTIFIED" and q.status is qmod.Status.CONCLUDED:
            out.append(
                Finding(
                    "warn",
                    "concluded-on-refusal",
                    f"{q.id} concluded although identification returned {q.verdict}; "
                    f"check no causal claim was made",
                )
            )
    return out


def _check_tables(cfg: Config) -> list[Finding]:
    out: list[Finding] = []
    if not cfg.tables_dir.exists():
        return out
    for path in sorted(cfg.tables_dir.rglob("*.md")):
        try:
            doc = frontmatter.load(path)
        except frontmatter.FrontmatterError as exc:
            out.append(Finding("error", "parse", str(exc)))
            continue
        columns = doc.meta.get("columns") or []
        if not isinstance(columns, list):
            out.append(
                Finding("error", "table", f"{path}: `columns` must be a list, got "
                                          f"{type(columns).__name__}")
            )
            continue
        for col in columns:
            if isinstance(col, dict) and not col.get("name"):
                out.append(Finding("error", "table", f"{path}: a column entry has no `name`"))
    return out


def report(findings: list[Finding]) -> str:
    if not findings:
        return "✓ clean"
    errors = [f for f in findings if f.level == "error"]
    warns = [f for f in findings if f.level == "warn"]
    lines = [str(f) for f in errors + warns]
    lines.append("")
    lines.append(f"{len(errors)} error(s), {len(warns)} warning(s)")
    return "\n".join(lines)
