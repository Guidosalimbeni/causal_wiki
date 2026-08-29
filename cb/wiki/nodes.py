"""Parse node files into nodes and typed edges.

One markdown file per variable. The heading gives the direction and the kind,
because Obsidian's graph view has neither:

    ## Caused by      incoming causal edges   (parent -> this node)
    ## Causes         outgoing causal edges   (this node -> child)
    ## Computed from  arithmetic edges        (never enters the causal graph)

Each entry is a wikilink, one line of reasoning, and an HTML comment holding the
machine fields. The comment keeps Obsidian's reading view clean while staying
greppable.

    - [[lead_time_days]] — renders only when lead_time > 60 <!-- cb: confirmed_by=guido -->
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Literal

from . import frontmatter

EdgeKind = Literal["causal", "arithmetic"]

CAUSED_BY = "caused by"
CAUSES = "causes"
COMPUTED_FROM = "computed from"

SECTION_KINDS: dict[str, tuple[EdgeKind, str]] = {
    # heading -> (edge kind, direction relative to the file's own node)
    CAUSED_BY: ("causal", "in"),
    CAUSES: ("causal", "out"),
    COMPUTED_FROM: ("arithmetic", "in"),
}

CAUSAL_ROLES = {
    "treatment",
    "outcome",
    "confounder",
    "mediator",
    "collider",
    "proxy",
    "instrument",
    "unspecified",
}

UNCONFIRMED = "claude-proposed"

_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(?P<title>.+?)\s*$")
_LIST_ITEM = re.compile(r"^\s*[-*+]\s+(?P<content>.*)$")
_WIKILINK = re.compile(r"\[\[(?P<target>[^\]|#]+?)(?:\#[^\]|]*)?(?:\|(?P<alias>[^\]]*))?\]\]")
_META = re.compile(r"<!--\s*cb:\s*(?P<body>.*?)\s*-->", re.DOTALL)
_META_PAIR = re.compile(r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<value>\[\[[^\]]+\]\]|\S+)")


class NodeError(ValueError):
    """A node file is malformed in a way that would corrupt the graph."""


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    kind: EdgeKind
    reason: str = ""
    meta: dict[str, str] = field(default_factory=dict)
    declared_in: str = ""
    line: int = 0

    @property
    def confirmed_by(self) -> str:
        return self.meta.get("confirmed_by", UNCONFIRMED)

    @property
    def confirmed_at(self) -> str:
        return self.meta.get("confirmed_at", "")

    @property
    def confirmed(self) -> bool:
        return self.confirmed_by != UNCONFIRMED

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.source, self.target, self.kind)


@dataclass
class Node:
    id: str
    meta: dict[str, Any] = field(default_factory=dict)
    body: str = ""
    edges: list[Edge] = field(default_factory=list)
    path: Path | None = None

    @property
    def observed(self) -> bool:
        # Absent means observed. Being unobserved is the claim that needs stating.
        return bool(self.meta.get("observed", True))

    @property
    def label(self) -> str:
        return str(self.meta.get("label", self.id))

    @property
    def graphs(self) -> list[str]:
        raw = self.meta.get("graphs") or []
        if isinstance(raw, str):
            return [raw]
        return [str(g) for g in raw]

    @property
    def causal_role(self) -> str:
        return str(self.meta.get("causal_role", "unspecified"))

    @property
    def computed_from(self) -> list[str]:
        return [e.source for e in self.edges if e.kind == "arithmetic" and e.target == self.id]


def parse_meta_comment(text: str) -> dict[str, str]:
    match = _META.search(text)
    if not match:
        return {}
    return {m.group("key"): m.group("value") for m in _META_PAIR.finditer(match.group("body"))}


def strip_meta_comment(text: str) -> str:
    return _META.sub("", text).strip()


def _normalise_heading(title: str) -> str:
    return title.strip().rstrip(":").strip().lower()


def parse_edges(node_id: str, body: str, declared_in: str = "") -> list[Edge]:
    """Walk the body, tracking which typed section we are in."""
    edges: list[Edge] = []
    current: tuple[EdgeKind, str] | None = None

    for lineno, line in enumerate(body.splitlines(), start=1):
        heading = _HEADING.match(line)
        if heading:
            current = SECTION_KINDS.get(_normalise_heading(heading.group("title")))
            continue
        if current is None:
            continue
        item = _LIST_ITEM.match(line)
        if not item:
            continue
        content = item.group("content")
        link = _WIKILINK.search(content)
        if not link:
            # A prose bullet such as "(none — arithmetic only)". Not an edge.
            continue

        kind, direction = current
        other = link.group("target").strip()
        # Wikilinks may carry a folder prefix; the node id is the basename.
        other = other.rsplit("/", 1)[-1]
        reason = strip_meta_comment(_WIKILINK.sub("", content, count=1))
        reason = reason.lstrip(" —-–:").strip()
        source, target = (other, node_id) if direction == "in" else (node_id, other)
        edges.append(
            Edge(
                source=source,
                target=target,
                kind=kind,
                reason=reason,
                meta=parse_meta_comment(content),
                declared_in=declared_in,
                line=lineno,
            )
        )
    return edges


def parse(path: Path) -> Node:
    doc = frontmatter.load(path)
    node_id = str(doc.meta.get("id") or Path(path).stem)
    if not node_id:
        raise NodeError(f"{path}: node has no id")
    role = doc.meta.get("causal_role")
    if role is not None and str(role) not in CAUSAL_ROLES:
        raise NodeError(
            f"{path}: causal_role '{role}' is not one of {sorted(CAUSAL_ROLES)}"
        )
    return Node(
        id=node_id,
        meta=doc.meta,
        body=doc.body,
        edges=parse_edges(node_id, doc.body, declared_in=str(path)),
        path=Path(path),
    )


def iter_node_files(graph_dir: Path) -> Iterator[Path]:
    """Node files are *.md under the graph dir; `_`-prefixed names are prose."""
    for path in sorted(Path(graph_dir).rglob("*.md")):
        if path.name.startswith("_") or any(p.startswith("_") for p in path.parts):
            continue
        yield path


def load_nodes(graph_dir: Path) -> dict[str, Node]:
    nodes: dict[str, Node] = {}
    for path in iter_node_files(graph_dir):
        node = parse(path)
        if node.id in nodes:
            raise NodeError(
                f"duplicate node id '{node.id}' in {path} and {nodes[node.id].path}"
            )
        nodes[node.id] = node
    return nodes
