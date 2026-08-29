"""Definitional expansion.

`net_revenue = revenue x (1 - churn)` is exactly true and says nothing about
cause. Excluding arithmetic edges from the causal graph is right; silently
dropping the node is not, because that edge may be the only thing connecting
the outcome to anything, and the question then gets refused for the wrong
reason.

So before identification we expand an arithmetically-defined endpoint into its
components and identify against each of those instead.
"""

from __future__ import annotations

import networkx as nx


def components(arithmetic: nx.DiGraph, node: str, _seen: set[str] | None = None) -> list[str]:
    """Resolve a node to the leaves of its definition, depth-first.

    A node with no arithmetic parents resolves to itself.
    """
    seen = _seen if _seen is not None else set()
    if node in seen:
        return []  # a circular definition; doctor reports it separately
    seen.add(node)

    if node not in arithmetic:
        return [node]
    parents = list(arithmetic.predecessors(node))
    if not parents:
        return [node]

    out: list[str] = []
    for parent in parents:
        for leaf in components(arithmetic, parent, seen):
            if leaf not in out:
                out.append(leaf)
    return out


def is_defined(arithmetic: nx.DiGraph, node: str) -> bool:
    return node in arithmetic and arithmetic.in_degree(node) > 0


def expansion(arithmetic: nx.DiGraph, targets: list[str]) -> dict[str, list[str]]:
    """Map each arithmetically-defined target to its components.

    Targets that are not defined arithmetically are absent from the result, so
    an empty dict means nothing needs re-posing.
    """
    return {
        node: components(arithmetic, node)
        for node in targets
        if is_defined(arithmetic, node)
    }


def describe(expanded: dict[str, list[str]]) -> str:
    parts = []
    for node, comps in expanded.items():
        parts.append(f"`{node}` is defined as an identity over {', '.join(f'`{c}`' for c in comps)}")
    return "; ".join(parts)
