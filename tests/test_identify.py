"""Golden identification tests against textbook DAGs with known answers.

These exist to break loudly if a DoWhy upgrade changes semantics, rather than
letting an unanswerable question get quietly certified.
"""

from __future__ import annotations

import pytest

from cb.identify import identify
from cb.identify.engine import GraphError
from cb.identify.report import Report, Verdict

from .helpers import wiki_from


def verdict_for(edges, observed, treatment="T", outcome="Y", **kw):
    wiki = wiki_from(edges, observed)
    return identify(wiki, [treatment], [outcome], **kw)


def test_backdoor_is_identified_and_names_the_adjustment_set():
    r = verdict_for([("W", "T"), ("W", "Y"), ("T", "Y")], observed={"W", "T", "Y"})
    assert r.verdict is Verdict.IDENTIFIED
    backdoor = next(s for s in r.strategies if s.kind == "backdoor")
    assert backdoor.variables == ["W"]


def test_bow_arc_is_refused_and_names_the_latent():
    """DoWhy does NOT raise here — it returns all-None estimands.

    This is the exact bug the guard exists for.
    """
    r = verdict_for([("U", "T"), ("U", "Y"), ("T", "Y")], observed={"T", "Y"})
    assert r.verdict is Verdict.NO_CRITERION_FOUND
    assert r.blocking_nodes == ["U"]
    assert "U" in r.design_alternative
    assert "Randomise" in r.design_alternative


def test_frontdoor_is_identified_despite_an_unblockable_backdoor_path():
    """The case a naive 'unobserved node on an open path -> refuse' rule breaks."""
    r = verdict_for(
        [("U", "T"), ("U", "Y"), ("T", "M"), ("M", "Y")], observed={"T", "M", "Y"}
    )
    assert r.verdict is Verdict.IDENTIFIED
    frontdoor = next(s for s in r.strategies if s.kind == "frontdoor")
    assert frontdoor.variables == ["M"]


def test_instrument_is_identified_despite_an_unblockable_backdoor_path():
    r = verdict_for(
        [("U", "T"), ("U", "Y"), ("Z", "T"), ("T", "Y")], observed={"Z", "T", "Y"}
    )
    assert r.verdict is Verdict.IDENTIFIED
    iv = next(s for s in r.strategies if s.kind == "iv")
    assert iv.variables == ["Z"]


def test_no_directed_path_is_reported_distinctly():
    """DoWhy's other failure shape: `estimands` is None, not a dict of Nones."""
    r = verdict_for([("T", "A"), ("B", "Y")], observed={"T", "Y", "A", "B"})
    assert r.verdict is Verdict.NO_DIRECTED_PATH
    assert "no directed path" in r.design_alternative.lower()


def test_m_bias_does_not_adjust_for_the_collider():
    """Adjusting for Z would open a path. The empty set is the right answer."""
    r = verdict_for(
        [("U1", "Z"), ("U1", "T"), ("U2", "Z"), ("U2", "Y"), ("T", "Y")],
        observed={"Z", "T", "Y"},
    )
    assert r.verdict is Verdict.IDENTIFIED
    backdoor = next(s for s in r.strategies if s.kind == "backdoor")
    assert backdoor.variables == []


def test_unobserved_instrument_is_discarded_not_certified():
    """DoWhy proposes the latent U1 as an instrument on the M-bias graph.

    Verified against dowhy 0.14: `estimands['iv']` is PRESENT and
    `get_instrumental_variables()` returns ['U1'], a node we declared
    unobserved. Accepting it would certify a design requiring a variable we
    have said we cannot measure.
    """
    r = verdict_for(
        [("U1", "Z"), ("U1", "T"), ("U2", "Z"), ("U2", "Y"), ("T", "Y")],
        observed={"Z", "T", "Y"},
    )
    assert not any(s.kind == "iv" for s in r.strategies)
    assert any("U1" in d for d in r.discarded_strategies)


def test_unobserved_confounder_with_no_alternative_is_refused():
    r = verdict_for([("W", "T"), ("W", "Y"), ("T", "Y")], observed={"T", "Y"})
    assert r.verdict is Verdict.NO_CRITERION_FOUND
    assert r.blocking_nodes == ["W"]


def test_cycle_raises_rather_than_producing_a_verdict():
    with pytest.raises(GraphError, match="cycle"):
        verdict_for([("T", "Y"), ("Y", "Z"), ("Z", "T")], observed={"T", "Y", "Z"})


def test_unknown_variable_raises():
    with pytest.raises(GraphError, match="no node file"):
        verdict_for([("T", "Y")], observed={"T", "Y"}, outcome="nonexistent")


class TestRefusalContract:
    """A refusal that names no alternative design must be impossible to write."""

    @pytest.mark.parametrize(
        "verdict",
        [Verdict.NO_CRITERION_FOUND, Verdict.NO_DIRECTED_PATH, Verdict.NEEDS_EXPANSION],
    )
    def test_refusal_without_a_design_fails_validation(self, verdict):
        with pytest.raises(ValueError, match="design_alternative"):
            Report(question_id="q", treatment=["T"], outcome=["Y"], verdict=verdict)

    def test_identified_needs_no_design_alternative(self):
        r = Report(
            question_id="q", treatment=["T"], outcome=["Y"], verdict=Verdict.IDENTIFIED
        )
        assert r.identified

    def test_every_refusal_from_the_engine_proposes_a_design(self):
        cases = [
            ([("U", "T"), ("U", "Y"), ("T", "Y")], {"T", "Y"}),
            ([("T", "A"), ("B", "Y")], {"T", "Y", "A", "B"}),
        ]
        for edges, observed in cases:
            r = verdict_for(edges, observed=observed)
            assert not r.identified
            assert r.design_alternative.strip()
