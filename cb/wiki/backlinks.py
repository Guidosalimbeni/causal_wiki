"""Which questions touched this variable — written back onto the node file.

The wiki is organised by concept and the questions by id, which is right: ten
churn questions add ten records but only ever one `churn_90d.md`. What was
missing is the way back. You could go question -> node by reading the record,
never node -> questions, so the only way to ask "what have we already learned
about churn" was to remember.

The answer belongs on the node, where anyone browsing the wiki — or Obsidian —
already is. It is generated, so it lives in a managed region and never touches
the prose a human wrote around it.
"""

from __future__ import annotations

import os
from pathlib import Path

from ..config import Config
from ..records import question as qmod
from . import managed
from .graph import Wiki

REGION = "questions"
HEADING = "## Questions asked here"


def _line(node_id: str, q: qmod.Question, from_dir: Path) -> str:
    target = os.path.relpath(q.path, from_dir).replace(os.sep, "/")
    roles = []
    if node_id in q.treatment:
        roles.append("treatment")
    if node_id in q.outcome:
        roles.append("outcome")
    parts = ["/".join(roles) or "mentioned", q.status.value]
    if q.verdict:
        parts.append(q.verdict)
    line = f"- [{q.id}]({target}) — {' · '.join(parts)} — {q.question}"
    if q.finding:
        # Two spaces: a continuation of the list item. Four or more would make
        # markdown read the finding as a code block.
        line += f"\n  {q.finding}"
    return line


def render(node_id: str, questions: list[qmod.Question], from_dir: Path) -> str:
    body = "\n".join(_line(node_id, q, from_dir) for q in questions)
    return f"{HEADING}\n\n{body}"


def update(cfg: Config, wiki: Wiki) -> list[Path]:
    """Refresh the backlink region on every node file. Returns what changed."""
    by_node: dict[str, list[qmod.Question]] = {}
    for q in qmod.iter_questions(cfg.questions):
        for node_id in sorted(q.nodes):
            by_node.setdefault(node_id, []).append(q)
    for questions in by_node.values():
        questions.sort(key=lambda q: q.id)

    changed: list[Path] = []
    for node_id, node in sorted(wiki.nodes.items()):
        if node.path is None:
            continue
        path = Path(node.path)
        before = path.read_text(encoding="utf-8")
        asked = by_node.get(node_id, [])
        # A node nobody has asked about carries no block at all, rather than an
        # empty one in every file.
        after = (
            managed.replace(before, render(node_id, asked, path.parent), name=REGION)
            if asked
            else managed.remove(before, name=REGION)
        )
        if after != before:
            path.write_text(after, encoding="utf-8")
            changed.append(path)
    return changed
