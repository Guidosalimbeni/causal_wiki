"""Turn a directory of node files into NetworkX graphs.

Two graphs come out, and keeping them apart is the whole point: `causal` holds
claims about mechanism, `arithmetic` holds definitional identities. An accounting
identity certified as a finding is the failure mode this separation prevents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx

from .nodes import Edge, Node, load_nodes

# Edge metadata keys that must agree when an edge is declared on both endpoints.
RECONCILED_KEYS = ("confirmed_by", "confirmed_at")


@dataclass
class Conflict:
    edge: tuple[str, str, str]
    key: str
    values: dict[str, str]  # file -> value

    def __str__(self) -> str:
        s, t, kind = self.edge
        where = "; ".join(f"{v!r} in {f}" for f, v in self.values.items())
        return f"{s} -> {t} ({kind}): contradictory {self.key}: {where}"


@dataclass
class Wiki:
    """The parsed graph layer of the wiki."""

    nodes: dict[str, Node] = field(default_factory=dict)
    edges: dict[tuple[str, str, str], Edge] = field(default_factory=dict)
    conflicts: list[Conflict] = field(default_factory=list)
    dangling: list[Edge] = field(default_factory=list)

    # -- graphs ---------------------------------------------------------------

    def causal(self) -> nx.DiGraph:
        return self._build("causal")

    def arithmetic(self) -> nx.DiGraph:
        return self._build("arithmetic")

    def _build(self, kind: str) -> nx.DiGraph:
        g = nx.DiGraph()
        for node_id, node in self.nodes.items():
            g.add_node(node_id, observed=node.observed, label=node.label, role=node.causal_role)
        for (s, t, k), edge in self.edges.items():
            if k != kind:
                continue
            for end in (s, t):
                if end not in g:
                    g.add_node(end, observed=True, label=end, role="unspecified")
            g.add_edge(s, t, reason=edge.reason, confirmed_by=edge.confirmed_by)
        return g

    # -- views ----------------------------------------------------------------

    def graph_names(self) -> list[str]:
        names: set[str] = set()
        for node in self.nodes.values():
            names.update(node.graphs)
        return sorted(names)

    def view(self, name: str) -> set[str]:
        """Node ids belonging to a named graph."""
        return {nid for nid, n in self.nodes.items() if name in n.graphs}

    def observed(self) -> set[str]:
        return {nid for nid, n in self.nodes.items() if n.observed}

    def unobserved(self) -> set[str]:
        return {nid for nid, n in self.nodes.items() if not n.observed}


def reconcile(all_edges: list[Edge]) -> tuple[dict[tuple[str, str, str], Edge], list[Conflict]]:
    """Union edges declared on either endpoint.

    Declaring the same edge from both sides is allowed and normal — it reads
    better in Obsidian. Only contradictory metadata is a problem.
    """
    merged: dict[tuple[str, str, str], Edge] = {}
    seen: dict[tuple[str, str, str], list[Edge] ] = {}
    for edge in all_edges:
        seen.setdefault(edge.key, []).append(edge)

    conflicts: list[Conflict] = []
    for key, group in seen.items():
        meta: dict[str, str] = {}
        for key_name in RECONCILED_KEYS:
            values = {e.declared_in: e.meta[key_name] for e in group if key_name in e.meta}
            distinct = set(values.values())
            if len(distinct) > 1:
                conflicts.append(Conflict(edge=key, key=key_name, values=values))
            if distinct:
                # Prefer a human confirmation over an unreviewed proposal.
                meta[key_name] = sorted(distinct)[0]
        for edge in group:
            for k, v in edge.meta.items():
                meta.setdefault(k, v)
        # A human-confirmed declaration wins as the representative.
        primary = next((e for e in group if e.confirmed), group[0])
        reason = next((e.reason for e in group if e.reason), "")
        merged[key] = Edge(
            source=key[0],
            target=key[1],
            kind=key[2],  # type: ignore[arg-type]
            reason=reason,
            meta=meta,
            declared_in=primary.declared_in,
            line=primary.line,
        )
    return merged, conflicts


def load(graph_dir: Path) -> Wiki:
    nodes = load_nodes(graph_dir)
    all_edges = [e for n in nodes.values() for e in n.edges]
    merged, conflicts = reconcile(all_edges)
    dangling = [e for e in merged.values() if e.source not in nodes or e.target not in nodes]
    return Wiki(nodes=nodes, edges=merged, conflicts=conflicts, dangling=dangling)


def restrict(g: nx.DiGraph, treatment: list[str], outcome: list[str]) -> nx.DiGraph:
    """Cut the graph to what can matter: ancestors of treatment and outcome.

    Identification only depends on this subgraph, and a smaller graph makes the
    verdict readable.
    """
    keep: set[str] = set()
    for node in list(treatment) + list(outcome):
        if node not in g:
            continue
        keep.add(node)
        keep |= nx.ancestors(g, node)
    # Descendants of the treatment that lead to the outcome carry mediators.
    for t in treatment:
        if t not in g:
            continue
        for o in outcome:
            if o not in g:
                continue
            for path in nx.all_simple_paths(g, t, o):
                keep.update(path)
    return g.subgraph(keep).copy()
