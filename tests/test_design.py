"""Experiments as a first-class answer, not a consolation prize.

Randomisation is the only design that rests on no untestable assumption, so it
has to be reachable in three situations: when nothing observational recovers the
effect, when the analyst asks for one outright, and when a finding that came out
clean deserves confirming. What is tested here is that each of those has a place
in the wiki and cannot silently evaporate.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from cb.records.question import DesignStatus, Question

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


def notebook(project, qid, pattern):
    import nbformat as nbf

    path = next((next(project.glob(f"questions/{qid}*")) / "notebooks").glob(pattern))
    return "\n".join(c.source for c in nbf.read(path, as_version=4).cells)


class TestTheRecord:
    def test_a_status_with_no_design_is_rejected(self):
        """"We should randomise it" is not a design until it says what runs."""
        with pytest.raises(ValueError, match="no design"):
            Question(id="q-0001", question="q", design_status="proposed")

    def test_a_design_that_ran_must_point_at_what_it_found(self):
        with pytest.raises(ValueError, match="requires experiment"):
            Question(id="q-0001", question="q", design="holdout", design_status="ran")

    def test_a_complete_record_round_trips(self, tmp_path):
        from cb.records import question as qmod

        q = qmod.create(tmp_path / "questions", "Do rep calls cause upgrades?")
        q.design = "10% account-level holdout, six weeks"
        q.design_status = DesignStatus.RUNNING
        q.save()
        assert qmod.load(q.dir).design_status is DesignStatus.RUNNING

    def test_doctor_catches_an_experiment_that_was_never_written_up(self, project):
        from cb.records import question as qmod

        q = qmod.find(project / "questions", "q-0002")
        q.design_status = DesignStatus.RAN
        q.experiment = "2026-q1-rep-call-holdout"
        q.save()
        out = cb("doctor", cwd=project, expect=1)
        assert "dangling-experiment" in out


class TestItCannotBeForgotten:
    def test_a_proposed_design_stays_visible(self, project):
        cb("index", cwd=project)
        out = cb("gaps", "--kind", "design-waiting", cwd=project)
        assert "q-0002" in out and "proposed" in out

    def test_a_refusal_with_no_design_is_reported(self, project):
        cb("index", cwd=project)
        out = cb("gaps", "--kind", "refusal-without-a-design", cwd=project)
        assert "q-0003" in out          # refused, nothing proposed
        assert "q-0002" not in out      # refused, design on the record

    def test_a_design_that_ran_stops_waiting(self, project):
        from cb.records import question as qmod

        q = qmod.find(project / "questions", "q-0002")
        q.design_status = DesignStatus.RAN
        q.experiment = "2025-q3-addon-holdout"
        q.save()
        cb("index", cwd=project)
        assert "no gaps found" in cb("gaps", "--kind", "design-waiting", cwd=project)

    def test_status_shows_where_the_experiment_stands(self, project):
        assert "[experiment proposed]" in cb("status", cwd=project)


class TestTheDesignNotebook:
    def test_a_refusal_gets_the_design_it_named(self, project):
        cb("notebook", "new", "q-0002", "--design", cwd=project)
        text = notebook(project, "q-0002", "design-*.ipynb")
        assert "sales_rep_effort" in text          # why the data cannot answer it
        assert "Randomise `rep_call_made`" in text

    def test_it_is_available_even_when_identified(self, project):
        """"Give me the design instead" is never refused."""
        cb("notebook", "new", "q-0001", "--design", cwd=project)
        text = notebook(project, "q-0001", "design-*.ipynb")
        assert "for confirmation" in text
        assert "two designs" in text.lower()

    def test_it_scaffolds_what_a_design_actually_needs(self, project):
        cb("notebook", "new", "q-0002", "--design", cwd=project)
        text = notebook(project, "q-0002", "design-*.ipynb")
        for essential in ("MDE", "n_per_arm", "Sample ratio mismatch", "GUARDRAILS",
                          "intention-to-treat", "Stopping rule", "CLUSTERED"):
            assert essential in text, essential

    def test_it_says_how_to_record_the_result(self, project):
        out = cb("notebook", "new", "q-0002", "--design", cwd=project)
        assert "design_status: proposed" in out
        text = notebook(project, "q-0002", "design-*.ipynb")
        assert "wiki/experiments/" in text

    def test_it_does_not_disturb_the_analysis_notebook(self, project):
        """A design is a route through the flow, not a stage of it."""
        before = (next(project.glob("questions/q-0001*")) / "question.md").read_text()
        cb("notebook", "new", "q-0001", "--design", cwd=project)
        after = (next(project.glob("questions/q-0001*")) / "question.md").read_text()
        assert after == before

    def test_the_design_is_logged(self, project):
        cb("notebook", "new", "q-0002", "--design", cwd=project)
        log = (next(project.glob("questions/q-0002*")) / "log.md").read_text()
        assert "design" in log


class TestDesignsAreMethods:
    def test_a_design_note_counts_the_questions_that_proposed_it(self, project):
        out = cb("methods", cwd=project)
        assert "randomised-holdout" in out
        assert "q-0002*" in out

    def test_the_note_lists_them(self, project):
        cb("index", cwd=project)
        text = (project / "wiki" / "methods" / "randomised-holdout.md").read_text()
        assert "## Questions that reached for this" in text
        assert "design proposed" in text

    def test_a_design_with_no_note_is_reported(self, project):
        from cb.records import question as qmod

        q = qmod.find(project / "questions", "q-0002")
        q.design = "Switchback across regions, two-week periods"
        q.save()
        out = cb("methods", cwd=project)
        assert "Reached for but never written up" in out
        assert "Switchback" in out
