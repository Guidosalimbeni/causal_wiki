"""Identification: can this effect be recovered from what we observe?

This is the one step that is code and not judgement. An LLM asked "is this
identified?" is usually right, and "usually" fails exactly when there is a
deadline and someone wants a number. That is the case the whole tool exists for.

Two guards wrap DoWhy, both verified against dowhy 0.14:

1. `identify_effect_auto` does NOT raise when an effect is unidentifiable. It
   returns an object whose estimands are all None — or, when the treatment
   cannot reach the outcome at all, whose `estimands` attribute is itself None.
   Both shapes are checked explicitly.

2. DoWhy will return an estimand that depends on a variable we told it was
   unobserved. On an M-bias graph with observed {Z,T,Y} it proposes the latent
   U1 as an instrument, with a full estimand expression. Trusting
   `estimands['iv'] is not None` would certify a question that requires
   measuring something we have said we cannot measure. So every strategy is
   filtered against the observed set before it counts.
"""

from __future__ import annotations

import networkx as nx

from ..wiki import graph as wikigraph
from ..wiki.graph import Wiki
from . import expand
from .report import Report, Strategy, Verdict

# Estimand keys whose presence we treat as a candidate strategy.
STRATEGY_KEYS = ("backdoor", "frontdoor", "iv", "general_adjustment")


class GraphError(ValueError):
    """The graph cannot be identified against at all."""


def _dowhy():
    # Imported lazily: ingest, doctor and index should not pay for scipy/sklearn.
    from dowhy.causal_identifier import identify_effect_auto
    from dowhy.causal_identifier.auto_identifier import EstimandType

    return identify_effect_auto, EstimandType


def _estimands(estimand) -> dict:
    """Normalise DoWhy's two failure shapes into one dict."""
    raw = getattr(estimand, "estimands", None)
    return raw if isinstance(raw, dict) else {}


def _present(estimands: dict, key: str) -> bool:
    return estimands.get(key) is not None


def _strategy_variables(estimand, kind: str) -> list[str]:
    getter = {
        "backdoor": "get_backdoor_variables",
        "frontdoor": "get_frontdoor_variables",
        "iv": "get_instrumental_variables",
        "general_adjustment": "get_general_adjustment_variables",
    }[kind]
    try:
        value = getattr(estimand, getter)()
    except Exception:
        return []
    # Sorted because DoWhy's ordering is not stable across runs: an adjustment
    # set is a set, so the order carries no meaning, but an unsorted one makes
    # identification.json and the generated notebook differ on every re-run.
    return sorted(str(v) for v in (value or []))


def _assumptions(estimands: dict, key: str, targets: list[str]) -> dict[str, str]:
    node = estimands.get(key)
    if isinstance(node, dict):
        raw = node.get("assumptions") or {}
        if isinstance(raw, dict):
            return {str(k): _mend(str(v), targets) for k, v in raw.items()}
    return {}


def _mend(text: str, targets: list[str]) -> str:
    """Repair DoWhy's assumption strings, which comma-join a bare string.

    dowhy 0.14 renders a single outcome `churn_90d` as `c,h,u,r,n,_,9,0,d`
    because it joins the string rather than the list containing it. The text is
    shown to the analyst next to the verdict, so a garbled version reads as a
    broken tool.
    """
    for name in targets:
        text = text.replace(",".join(name), name)
    return text


def unobserved_common_causes(g: nx.DiGraph, treatment: list[str], outcome: list[str]) -> list[str]:
    """Unobserved nodes that are ancestors of both treatment and outcome.

    These are the nodes to name in a refusal: they open a backdoor path no
    observed set can block.
    """
    def ancestors(nodes: list[str]) -> set[str]:
        out: set[str] = set()
        for n in nodes:
            if n in g:
                out |= nx.ancestors(g, n)
        return out

    both = ancestors(treatment) & ancestors(outcome)
    return sorted(n for n in both if not g.nodes[n].get("observed", True))


def _propose_design(
    verdict: Verdict,
    treatment: list[str],
    outcome: list[str],
    blocking: list[str],
    expanded: dict[str, list[str]],
) -> str:
    t = ", ".join(f"`{x}`" for x in treatment) or "the treatment"
    y = ", ".join(f"`{x}`" for x in outcome) or "the outcome"

    if verdict is Verdict.NEEDS_EXPANSION:
        return (
            f"{expand.describe(expanded)}. An identity is exactly true and carries no "
            f"causal content, so the effect on it is not a causal quantity. Re-pose the "
            f"question against the components listed above — ask about each separately, "
            f"then recombine through the identity if a headline number is wanted."
        )

    if verdict is Verdict.NO_DIRECTED_PATH:
        return (
            f"The graph contains no directed path from {t} to {y}, so as drawn the "
            f"treatment cannot affect the outcome and there is no effect to estimate. "
            f"Either the graph is missing an edge — if you believe a mechanism exists, "
            f"add it in the interview and re-run — or the honest answer to the business "
            f"is that this intervention cannot move this metric."
        )

    # NO_CRITERION_FOUND
    named = ", ".join(f"`{b}`" for b in blocking)
    lines = []
    if blocking:
        lines.append(
            f"{named} {'is an unobserved common cause' if len(blocking) == 1 else 'are unobserved common causes'} "
            f"of {t} and {y}, and no observed set blocks the backdoor path it opens."
        )
    else:
        lines.append(
            f"No backdoor, frontdoor or instrumental-variable strategy over the observed "
            f"variables recovers the effect of {t} on {y}."
        )
    lines.append("Designs that would work, in rough order of cost:")
    if blocking:
        lines.append(
            f"1. **Measure {named}.** If a proxy exists in the warehouse, add it as a node "
            f"and re-run — a good proxy may close the path."
        )
    lines.append(
        f"{'2' if blocking else '1'}. **Randomise {t}.** An experiment removes every backdoor "
        f"path by construction and is the only design that needs no further assumptions."
    )
    lines.append(
        f"{'3' if blocking else '2'}. **Find an instrument** — something that shifts {t}, is "
        f"unrelated to {y} except through {t}, and is already recorded. A policy threshold, a "
        f"rollout date or a capacity constraint is often one."
    )
    lines.append(
        f"{'4' if blocking else '3'}. **Find a full mediator** — a measured variable that carries "
        f"the entire effect of {t} on {y}, which makes a frontdoor argument available."
    )
    return "\n".join(lines)


def _unconfirmed_on_paths(wiki: Wiki, g: nx.DiGraph) -> list[str]:
    """Edges in scope that nobody has confirmed.

    This replaces the approval queue: the pressure to confirm an edge arrives
    when it is load-bearing for an actual verdict, not as a backlog of 29 items.
    """
    out = []
    for (s, t, kind), edge in wiki.edges.items():
        if kind != "causal" or not g.has_edge(s, t) or edge.confirmed:
            continue
        out.append(f"`{s}` -> `{t}` ({edge.reason or 'no reasoning recorded'})")
    return sorted(out)


def identify(
    wiki: Wiki,
    treatment: list[str],
    outcome: list[str],
    question_id: str = "adhoc",
    graph_name: str | None = None,
) -> Report:
    causal = wiki.causal()
    arithmetic = wiki.arithmetic()

    missing = [n for n in treatment + outcome if n not in wiki.nodes]
    if missing:
        raise GraphError(
            f"no node file for: {', '.join(missing)}. "
            f"Every variable in a question must exist in the wiki before it can be identified."
        )

    if graph_name:
        keep = wiki.view(graph_name)
        if not keep:
            raise GraphError(f"no nodes belong to graph '{graph_name}'")
        missing_from_view = [n for n in treatment + outcome if n not in keep]
        if missing_from_view:
            raise GraphError(
                f"{', '.join(missing_from_view)} not in graph '{graph_name}' "
                f"(add '{graph_name}' to the node's `graphs:` list)"
            )
        causal = causal.subgraph(keep).copy()

    if not nx.is_directed_acyclic_graph(causal):
        cycle = nx.find_cycle(causal)
        pretty = " -> ".join(a for a, _ in cycle) + f" -> {cycle[-1][1]}"
        raise GraphError(
            f"the causal graph contains a cycle: {pretty}. "
            f"Identification is undefined on a cyclic graph; fix the node files first."
        )

    base = dict(
        question_id=question_id,
        treatment=treatment,
        outcome=outcome,
        graph=graph_name,
        dowhy_version=_version(),
    )

    # -- 1. definitional expansion, before anything else --------------------
    expanded = expand.expansion(arithmetic, treatment + outcome)
    if expanded:
        return Report(
            **base,
            verdict=Verdict.NEEDS_EXPANSION,
            expansion=expanded,
            design_alternative=_propose_design(
                Verdict.NEEDS_EXPANSION, treatment, outcome, [], expanded
            ),
            notes=["Arithmetic edges are excluded from the causal graph by construction."],
        )

    scoped = wikigraph.restrict(causal, treatment, outcome)
    observed = sorted(n for n in scoped if scoped.nodes[n].get("observed", True))
    unobserved = sorted(n for n in scoped if not scoped.nodes[n].get("observed", True))
    blocking = unobserved_common_causes(scoped, treatment, outcome)
    unconfirmed = _unconfirmed_on_paths(wiki, scoped)

    base |= dict(
        observed=observed,
        unobserved=unobserved,
        provisional=bool(unconfirmed),
        unconfirmed_edges=unconfirmed,
    )

    # -- 2. ask DoWhy --------------------------------------------------------
    identify_effect_auto, EstimandType = _dowhy()
    estimand = identify_effect_auto(
        scoped,
        treatment,
        outcome,
        observed,
        estimand_type=EstimandType.NONPARAMETRIC_ATE,
    )

    # -- 3. the guard: DoWhy does not raise on an unidentifiable effect ------
    if getattr(estimand, "no_directed_path", False):
        return Report(
            **base,
            verdict=Verdict.NO_DIRECTED_PATH,
            design_alternative=_propose_design(
                Verdict.NO_DIRECTED_PATH, treatment, outcome, blocking, {}
            ),
        )

    estimands = _estimands(estimand)

    # -- 4. the second guard: strategies that leak unobserved variables ------
    strategies: list[Strategy] = []
    discarded: list[str] = []
    observed_set = set(observed)

    for kind in STRATEGY_KEYS:
        if not _present(estimands, kind):
            continue
        variables = _strategy_variables(estimand, kind)
        leaked = [v for v in variables if v not in observed_set]
        if leaked:
            discarded.append(
                f"{kind}: DoWhy proposed {', '.join(f'`{v}`' for v in leaked)}, "
                f"which {'is' if len(leaked) == 1 else 'are'} marked unobserved in the wiki. "
                f"An estimand that needs an unmeasured variable is not a usable design."
            )
            continue
        strategies.append(
            Strategy(
                kind=kind,
                variables=variables,
                assumptions=_assumptions(estimands, kind, treatment + outcome),
                note=_note_for(kind, variables),
            )
        )

    if not strategies:
        return Report(
            **base,
            verdict=Verdict.NO_CRITERION_FOUND,
            blocking_nodes=blocking,
            discarded_strategies=discarded,
            design_alternative=_propose_design(
                Verdict.NO_CRITERION_FOUND, treatment, outcome, blocking, {}
            ),
        )

    return Report(
        **base,
        verdict=Verdict.IDENTIFIED,
        strategies=strategies,
        blocking_nodes=blocking,
        discarded_strategies=discarded,
    )


def _note_for(kind: str, variables: list[str]) -> str:
    if kind in ("backdoor", "general_adjustment") and not variables:
        return "No adjustment needed — no open backdoor path."
    return {
        "backdoor": "Adjust for these and the backdoor paths are blocked.",
        "general_adjustment": "A generalised adjustment set; equivalent to backdoor here.",
        "frontdoor": "These fully mediate the effect; estimate in two stages.",
        "iv": "Instrument(s); the exclusion restriction is an assumption the graph cannot verify.",
    }.get(kind, "")


def _version() -> str:
    try:
        import dowhy

        return str(dowhy.__version__)
    except Exception:
        return "unknown"
