"""Question records, definitional expansion, and validation."""

from __future__ import annotations

import networkx as nx
import pytest

from cb.identify import identify
from cb.identify.expand import components, expansion, is_defined
from cb.identify.report import Verdict
from cb.records import question as qmod
from cb.records.interview import Interview, Turn
from cb.records.result import notebook_to_markdown

from .helpers import wiki_from


class TestQuestionLifecycle:
    def test_create_allocates_sequential_ids(self, tmp_path):
        a = qmod.create(tmp_path, "first question")
        b = qmod.create(tmp_path, "second question")
        assert (a.id, b.id) == ("q-0001", "q-0002")

    def test_the_record_round_trips(self, tmp_path):
        q = qmod.create(tmp_path, "does X cause Y", asked_by="guido")
        q.treatment, q.outcome = ["x"], ["y"]
        q.save()
        assert qmod.load(q.dir).treatment == ["x"]

    def test_every_stage_hangs_off_the_id(self, tmp_path):
        q = qmod.create(tmp_path, "a question")
        assert q.notebooks_dir.exists() and q.results_dir.exists()
        assert q.interview_path.parent == q.dir
        assert q.identification_path.parent == q.dir

    def test_the_log_accumulates(self, tmp_path):
        q = qmod.create(tmp_path, "a question")
        q.stamp("identify", "IDENTIFIED")
        text = q.log_path.read_text()
        assert "asked" in text and "identify" in text

    def test_slug_is_readable(self):
        assert qmod.slugify("Does the add-on reduce churn?") == "add-on-reduce-churn"


class TestAbandoningRequiresAReason:
    """The questions we drop are the ones worth learning from."""

    def test_abandoning_without_a_reason_fails(self):
        with pytest.raises(ValueError, match="abandoned_reason"):
            qmod.Question(id="q-0001", question="q", status=qmod.Status.ABANDONED)

    def test_a_blank_reason_is_not_a_reason(self):
        with pytest.raises(ValueError, match="abandoned_reason"):
            qmod.Question(
                id="q-0001", question="q", status=qmod.Status.ABANDONED, abandoned_reason="   "
            )

    def test_abandoning_with_a_reason_is_fine(self):
        q = qmod.Question(
            id="q-0001",
            question="q",
            status=qmod.Status.ABANDONED,
            abandoned_reason="no way to measure rep effort; revisit after the CRM change",
        )
        assert q.status is qmod.Status.ABANDONED


class TestDefinitionalExpansion:
    """net_revenue = revenue x (1 - churn) is exactly true and says nothing about cause."""

    def _wiki(self):
        return wiki_from(
            [("addon", "churn"), ("addon", "revenue")],
            observed={"addon", "churn", "revenue", "net_revenue"},
            arithmetic=[("revenue", "net_revenue"), ("churn", "net_revenue")],
        )

    def test_an_arithmetic_outcome_is_not_identified_but_re_posed(self):
        r = identify(self._wiki(), ["addon"], ["net_revenue"])
        assert r.verdict is Verdict.NEEDS_EXPANSION
        assert set(r.expansion["net_revenue"]) == {"revenue", "churn"}

    def test_the_re_posed_question_identifies(self):
        r = identify(self._wiki(), ["addon"], ["churn"])
        assert r.verdict is Verdict.IDENTIFIED

    def test_arithmetic_edges_stay_out_of_the_causal_graph(self):
        causal = self._wiki().causal()
        assert not causal.has_edge("revenue", "net_revenue")
        assert causal.has_edge("addon", "revenue")

    def test_the_refusal_says_how_to_re_pose(self):
        r = identify(self._wiki(), ["addon"], ["net_revenue"])
        assert "identity" in r.design_alternative
        assert "revenue" in r.design_alternative

    def test_components_resolve_recursively(self):
        g = nx.DiGraph([("a", "b"), ("b", "c")])
        assert components(g, "c") == ["a"]

    def test_a_node_with_no_definition_resolves_to_itself(self):
        assert components(nx.DiGraph(), "x") == ["x"]
        assert not is_defined(nx.DiGraph(), "x")

    def test_a_circular_definition_terminates(self):
        g = nx.DiGraph([("a", "b"), ("b", "a")])
        assert components(g, "a") == []  # doctor reports the cycle separately

    def test_nothing_to_expand_yields_an_empty_map(self):
        assert expansion(nx.DiGraph(), ["x", "y"]) == {}


class TestProvisionalVerdicts:
    """Replaces the approval queue: pressure arrives when an edge is load-bearing."""

    def test_an_unconfirmed_edge_in_scope_makes_the_verdict_provisional(self):
        wiki = wiki_from(
            [("w", "t"), ("w", "y"), ("t", "y")],
            observed={"w", "t", "y"},
            unconfirmed={("t", "y")},
        )
        r = identify(wiki, ["t"], ["y"])
        assert r.identified and r.provisional
        assert any("`t` -> `y`" in e for e in r.unconfirmed_edges)

    def test_a_fully_confirmed_graph_is_not_provisional(self):
        wiki = wiki_from([("w", "t"), ("w", "y"), ("t", "y")], observed={"w", "t", "y"})
        assert not identify(wiki, ["t"], ["y"]).provisional


class TestInterview:
    def test_searchable_text_flattens_the_turns(self):
        i = Interview(
            question_id="q-0001",
            turns=[Turn(asked="how are they assigned?", answered="there is a rule")],
            assumptions=["the rule did not change"],
        )
        text = i.searchable_text()
        assert "there is a rule" in text and "the rule did not change" in text

    def test_unknown_keys_survive(self, tmp_path):
        from cb.records.interview import load

        i = Interview(question_id="q-0001", something_new="kept")
        path = i.save(tmp_path / "interview.yaml")
        assert load(path).something_new == "kept"


class TestBringingResultsBack:
    def test_a_failed_notebook_is_kept_and_flagged(self, tmp_path):
        import nbformat as nbf

        nb = nbf.v4.new_notebook()
        cell = nbf.v4.new_code_cell("refute()")
        cell.outputs = [
            nbf.v4.new_output("error", ename="ValueError", evalue="boom", traceback=["boom"])
        ]
        nb.cells = [cell]
        path = tmp_path / "nb.ipynb"
        nbf.write(nb, path)

        text = notebook_to_markdown(path)
        assert "boom" in text
        assert "the runs that fail are the ones worth keeping" in text

    def test_outputs_are_rendered(self, tmp_path):
        import nbformat as nbf

        nb = nbf.v4.new_notebook()
        cell = nbf.v4.new_code_cell("print(est)")
        cell.outputs = [nbf.v4.new_output("stream", name="stdout", text="Mean value: -0.02\n")]
        nb.cells = [cell]
        path = tmp_path / "nb.ipynb"
        nbf.write(nb, path)
        assert "Mean value: -0.02" in notebook_to_markdown(path)
