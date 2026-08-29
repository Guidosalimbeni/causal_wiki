"""Doctor catches the errors that silently corrupt every verdict downstream."""

from __future__ import annotations

import pytest

from cb import doctor
from cb.config import Config


@pytest.fixture
def project(tmp_path):
    cfg = Config(root=tmp_path)
    for d in cfg.dirs():
        d.mkdir(parents=True, exist_ok=True)
    return cfg


def node(cfg, nid: str, body: str = "", **meta):
    front = "\n".join(f"{k}: {v}" for k, v in {"id": nid, **meta}.items())
    (cfg.graph_dir / f"{nid}.md").write_text(f"---\n{front}\n---\n\n{body}\n")


def checks(cfg, level: str | None = None) -> set[str]:
    return {f.check for f in doctor.check(cfg) if level is None or f.level == level}


CONFIRMED = "<!-- cb: confirmed_by=guido -->"


class TestGraphCorruption:
    def test_an_arithmetic_edge_mistyped_as_causal_is_caught(self, project):
        """An accounting identity certified as a finding is the failure to prevent."""
        node(project, "revenue")
        node(
            project,
            "net_revenue",
            f"## Computed from\n- [[revenue]] {CONFIRMED}\n\n"
            f"## Caused by\n- [[revenue]] {CONFIRMED}\n",
        )
        assert "edge-kind-clash" in checks(project, "error")

    def test_a_cycle_is_caught(self, project):
        node(project, "a", f"## Causes\n- [[b]] {CONFIRMED}\n")
        node(project, "b", f"## Causes\n- [[c]] {CONFIRMED}\n")
        node(project, "c", f"## Causes\n- [[a]] {CONFIRMED}\n")
        assert "causal-cycle" in checks(project, "error")

    def test_a_circular_definition_is_caught(self, project):
        node(project, "a", f"## Computed from\n- [[b]] {CONFIRMED}\n")
        node(project, "b", f"## Computed from\n- [[a]] {CONFIRMED}\n")
        assert "arithmetic-cycle" in checks(project, "error")

    def test_a_link_to_a_missing_node_is_caught(self, project):
        node(project, "a", f"## Causes\n- [[typo_nobody_made_a_file_for]] {CONFIRMED}\n")
        assert "dangling-link" in checks(project, "error")

    def test_contradictory_confirmations_are_caught(self, project):
        node(project, "a", "## Causes\n- [[b]] <!-- cb: confirmed_by=guido -->\n")
        node(project, "b", "## Caused by\n- [[a]] <!-- cb: confirmed_by=someone_else -->\n")
        assert "contradictory-edge" in checks(project, "error")

    def test_a_malformed_file_is_reported_not_raised(self, project):
        (project.graph_dir / "broken.md").write_text("no frontmatter here\n")
        assert "parse" in checks(project, "error")

    def test_a_clean_graph_has_no_errors(self, project):
        node(project, "a", f"## Causes\n- [[b]] — a mechanism {CONFIRMED}\n", graphs="[g]")
        node(project, "b", graphs="[g]")
        assert not checks(project, "error")


class TestWarnings:
    def test_an_unconfirmed_edge_warns_without_blocking(self, project):
        node(project, "a", "## Causes\n- [[b]] — guessed\n", graphs="[g]")
        node(project, "b", graphs="[g]")
        assert "unconfirmed-edge" in checks(project, "warn")
        assert not checks(project, "error")

    def test_an_unsourced_latent_warns(self, project):
        node(project, "u", graphs="[g]", observed="false")
        assert "unsourced-latent" in checks(project, "warn")

    def test_a_node_in_no_graph_warns(self, project):
        node(project, "a")
        assert "ungrouped-node" in checks(project, "warn")


class TestQuestionChecks:
    def test_an_abandoned_question_without_a_reason_is_caught(self, project):
        d = project.questions / "q-0001-x"
        d.mkdir(parents=True)
        (d / "question.md").write_text("---\nid: q-0001\nquestion: x\nstatus: abandoned\n---\n")
        assert "question" in checks(project, "error")

    def test_concluding_on_a_refusal_warns(self, project):
        d = project.questions / "q-0001-x"
        d.mkdir(parents=True)
        (d / "question.md").write_text(
            "---\nid: q-0001\nquestion: x\nstatus: concluded\n"
            "verdict: NO_CRITERION_FOUND\n---\n"
        )
        assert "concluded-on-refusal" in checks(project, "warn")


def test_report_is_readable(project):
    node(project, "a", f"## Causes\n- [[missing]] {CONFIRMED}\n")
    text = doctor.report(doctor.check(project))
    assert "error(s)" in text
    assert doctor.report([]) == "✓ clean"
