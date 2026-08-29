"""Test helpers: build a Wiki in memory without touching the filesystem."""

from __future__ import annotations

from cb.wiki.graph import Wiki, reconcile
from cb.wiki.nodes import Edge, Node


def wiki_from(
    edges: list[tuple[str, str]],
    observed: set[str],
    *,
    arithmetic: list[tuple[str, str]] | None = None,
    graphs: dict[str, list[str]] | None = None,
    unconfirmed: set[tuple[str, str]] | None = None,
) -> Wiki:
    """Build a Wiki from edge tuples.

    Any node appearing in an edge gets a node file; `observed` lists which are
    measurable. Edges are confirmed unless listed in `unconfirmed`.
    """
    arithmetic = arithmetic or []
    graphs = graphs or {}
    unconfirmed = unconfirmed or set()

    ids = {n for e in list(edges) + list(arithmetic) for n in e} | set(observed)
    nodes = {
        nid: Node(
            id=nid,
            meta={
                "id": nid,
                "observed": nid in observed,
                "graphs": graphs.get(nid, []),
            },
        )
        for nid in sorted(ids)
    }

    parsed: list[Edge] = []
    for kind, pairs in (("causal", edges), ("arithmetic", arithmetic)):
        for s, t in pairs:
            meta = {} if (s, t) in unconfirmed else {"confirmed_by": "tester"}
            parsed.append(
                Edge(source=s, target=t, kind=kind, meta=meta, declared_in=f"{t}.md")
            )

    for edge in parsed:
        nodes[edge.target].edges.append(edge)

    merged, conflicts = reconcile(parsed)
    return Wiki(nodes=nodes, edges=merged, conflicts=conflicts)
