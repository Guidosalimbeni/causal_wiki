"""What has to keep working once a project holds hundreds of questions.

One question a day across a few analysts is the shape this tool is used in, and
every check here guards something that was fine at twenty questions and broken,
useless or unreadable at three hundred.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from cb import context as context_mod
from cb.config import Config
from cb.records import question as qmod

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "toy-company"


def cb(*args, cwd, expect=0):
    proc = subprocess.run(
        [sys.executable, "-m", "cb.cli", *args], cwd=cwd, capture_output=True, text=True
    )
    assert proc.returncode == expect, f"cb {' '.join(args)} -> {proc.returncode}\n{proc.stderr}"
    return proc.stdout


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "toy"
    shutil.copytree(EXAMPLE, root, ignore=shutil.ignore_patterns(".cb"))
    return root


class TestSearch:
    """Ranked search is the whole answer to "will this stay findable"."""

    def test_terms_need_not_be_adjacent(self, project):
        """A question and its interview share a `ref`. Keying the full-text
        index on it meant every search silently fell back to a substring LIKE,
        which finds nothing unless the words happen to sit next to each other."""
        cb("index", cwd=project)
        out = cb("find", "add-on churn", cwd=project)
        assert "naive-addon-churn-comparison" in out

    def test_an_interview_and_its_question_are_both_searchable(self, project):
        cb("index", cwd=project)
        out = cb("sql", "SELECT doc_id FROM docs WHERE ref = 'q-0001'", cwd=project)
        assert "question:q-0001" in out and "interview:q-0001" in out

    def test_document_ids_are_unique(self, project):
        cb("index", cwd=project)
        out = cb(
            "sql",
            "SELECT count(*) - count(DISTINCT doc_id) FROM docs",
            cwd=project,
        )
        assert out.strip().splitlines()[-1] == "0"


class TestContextPack:
    """The pack is read by Claude on every question. Unranked, it drowns."""

    def test_a_prior_sharing_a_variable_outranks_one_that_does_not(self, project):
        cfg = Config(root=project)
        q = qmod.find(cfg.questions, "q-0003")
        ranked = context_mod.rank_priors(cfg, q)
        assert [r.question.id for r in ranked][0] == "q-0001"
        assert "shares addon_shown" in ranked[0].reason

    def test_the_question_itself_is_never_a_prior(self, project):
        cfg = Config(root=project)
        q = qmod.find(cfg.questions, "q-0001")
        assert "q-0001" not in [r.question.id for r in context_mod.rank_priors(cfg, q)]

    def test_the_tail_is_counted_not_dropped(self, project):
        out = cb("context", "q-0003", "--limit", "1", cwd=project)
        assert "Prior questions (1 of 2" in out
        assert "…and 1 more" in out

    def test_all_lifts_the_cap(self, project):
        out = cb("context", "q-0003", "--limit", "1", "--all", cwd=project)
        assert "q-0001" in out and "q-0002" in out
        assert "…and" not in out


class TestStatus:
    def test_closed_questions_are_counted_not_listed(self, project):
        out = cb("status", cwd=project)
        assert "q-0001" not in out
        assert "1 concluded or abandoned, not shown" in out

    def test_all_shows_everything(self, project):
        assert "q-0001" in cb("status", "--all", cwd=project)

    def test_filtering_by_status(self, project):
        out = cb("status", "--status", "concluded", cwd=project)
        assert "q-0001" in out and "q-0002" not in out


class TestAgeing:
    def test_last_activity_comes_from_the_log(self, project):
        qdir = next(project.glob("questions/q-0002*"))
        (qdir / "log.md").write_text("# Log\n\n- `2020-01-01T00:00:00` **asked**\n")
        assert qmod.load(qdir).last_activity.startswith("2020-01-01")

    def test_last_activity_falls_back_to_the_asked_date(self, project):
        qdir = next(project.glob("questions/q-0002*"))
        (qdir / "log.md").unlink()
        q = qmod.load(qdir)
        assert q.last_activity == q.asked_on

    def test_a_question_in_flight_is_not_stalled(self, project):
        cb("index", cwd=project)
        assert "stalled-question" not in cb("gaps", cwd=project)

    def test_a_forgotten_question_is(self, project):
        qdir = next(project.glob("questions/q-0002*"))
        (qdir / "log.md").write_text("# Log\n\n- `2020-01-01T00:00:00` **asked**\n")
        cb("index", cwd=project)
        out = cb("gaps", "--kind", "stalled-question", cwd=project)
        assert "q-0002" in out and "q-0003" not in out


class TestDuplicates:
    def test_asking_the_same_thing_twice_is_flagged(self, project):
        out = cb("ask", "Does showing the flexible dates add-on reduce cancellations?",
                 cwd=project)
        assert "looks close to something already asked" in out
        assert "q-0001" in out

    def test_an_unrelated_question_is_not(self, project):
        out = cb("ask", "Do discounts change repeat purchase?", cwd=project)
        assert "looks close" not in out

    def test_a_collided_id_is_an_error(self, project):
        """Two analysts on two branches both get max+1. The merge is where it
        shows up, and by then the id is in paths and cross references."""
        src = next(project.glob("questions/q-0002*"))
        shutil.copytree(src, project / "questions" / "q-0002-asked-on-another-branch")
        out = cb("doctor", cwd=project, expect=1)
        assert "duplicate-question-id" in out


class TestBacklinks:
    def test_a_node_lists_the_questions_that_used_it(self, project):
        cb("index", cwd=project)
        text = (project / "wiki" / "graph" / "churn_90d.md").read_text()
        assert "## Questions asked here" in text
        assert "q-0001" in text
        assert "outcome · concluded · IDENTIFIED" in text

    def test_an_untouched_node_carries_no_block(self, project):
        cb("index", cwd=project)
        text = (project / "wiki" / "graph" / "account_size.md").read_text()
        assert "Questions asked here" not in text

    def test_regenerating_changes_nothing(self, project):
        cb("index", cwd=project)
        before = (project / "wiki" / "graph" / "churn_90d.md").read_text()
        cb("index", cwd=project)
        assert (project / "wiki" / "graph" / "churn_90d.md").read_text() == before

    def test_the_human_prose_is_left_alone(self, project):
        node = project / "wiki" / "graph" / "addon_purchased.md"
        before = node.read_text()
        cb("index", cwd=project)
        after = node.read_text()
        assert "Adjusting for it when asking about the" in after
        assert after.count("## Caused by") == before.count("## Caused by")

    def test_the_block_goes_when_the_question_does(self, project):
        cb("index", cwd=project)
        shutil.rmtree(next(project.glob("questions/q-0001*")))
        cb("index", cwd=project)
        text = (project / "wiki" / "graph" / "churn_90d.md").read_text()
        assert "Questions asked here" not in text

    def test_a_backlink_block_is_not_read_as_an_edge(self, project):
        """Generated links must never become causal claims."""
        cb("index", cwd=project)
        assert "✓ clean" in cb("doctor", cwd=project)
        before = cb("graph", "show", cwd=project)
        cb("index", cwd=project)
        assert cb("graph", "show", cwd=project) == before
