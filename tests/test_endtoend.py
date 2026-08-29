"""Walk all five stages, and verify the shipped example behaves as documented."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "toy-company"


def cb(*args, cwd, expect=0):
    proc = subprocess.run(
        [sys.executable, "-m", "cb.cli", *args], cwd=cwd, capture_output=True, text=True
    )
    assert proc.returncode == expect, f"cb {' '.join(args)} -> {proc.returncode}\n{proc.stderr}"
    return proc.stdout


@pytest.fixture
def project(tmp_path):
    """A copy of the shipped example, so tests never mutate it."""
    root = tmp_path / "toy"
    shutil.copytree(EXAMPLE, root, ignore=shutil.ignore_patterns(".cb"))
    return root


class TestShippedExample:
    def test_it_is_clean(self, project):
        assert "✓ clean" in cb("doctor", cwd=project)

    def test_the_backdoor_question_is_identified(self, project):
        out = cb("identify", "q-0001", cwd=project)
        assert "IDENTIFIED" in out
        report = json.loads((next(project.glob("questions/q-0001*")) / "identification.json").read_text())
        backdoor = next(s for s in report["strategies"] if s["kind"] == "backdoor")
        assert sorted(backdoor["variables"]) == ["booking_value", "lead_time_days"]

    def test_the_latent_question_is_refused_and_names_the_node(self, project):
        out = cb("identify", "q-0002", cwd=project, expect=2)
        assert "NO_CRITERION_FOUND" in out
        assert "sales_rep_effort" in out
        assert "Randomise" in out

    def test_a_refusal_exits_non_zero(self, project):
        """So a script can never mistake a refusal for an answer."""
        cb("identify", "q-0002", cwd=project, expect=2)

    def test_the_arithmetic_outcome_is_re_posed(self, project):
        out = cb("identify", "q-0003", cwd=project, expect=2)
        assert "NEEDS_EXPANSION" in out
        assert "revenue" in out and "churn_90d" in out

    def test_the_two_named_graphs_stay_separate(self, project):
        out = cb("graph", "list", cwd=project)
        assert "addon_uptake" in out and "rep_outreach" in out
        assert "sales_rep_effort" in out


class TestFiveStages:
    def test_the_whole_loop(self, project, tmp_path):
        import nbformat as nbf

        # 1. collect
        cb("ingest", cwd=project)

        # 2. a question arrives
        out = cb("ask", "Does the eligibility threshold change cancellations?", cwd=project)
        qid = out.split()[0]
        assert qid.startswith("q-")
        qdir = next(project.glob(f"questions/{qid}*"))

        # 3. the interview writes treatment/outcome
        text = (qdir / "question.md").read_text()
        (qdir / "question.md").write_text(
            text.replace(
                "status: draft",
                "status: interviewing\ntreatment:\n- addon_shown\noutcome:\n- churn_90d",
            )
        )
        cb("identify", qid, cwd=project)
        assert (qdir / "identification.json").exists()

        # 4. the notebook
        cb("notebook", "new", qid, cwd=project)
        nb_path = next((qdir / "notebooks").glob("*.ipynb"))
        nb = nbf.read(nb_path, as_version=4)
        assert "ADJUSTMENT_SET = ['booking_value', 'lead_time_days']" in nb.cells[1].source

        # 5. it comes back, run elsewhere
        executed = tmp_path / "run.ipynb"
        out_nb = nbf.v4.new_notebook()
        cell = nbf.v4.new_code_cell("print(est)")
        cell.outputs = [nbf.v4.new_output("stream", name="stdout", text="Mean value: -0.021\n")]
        out_nb.cells = [cell]
        nbf.write(out_nb, executed)

        cb("result", "add", qid, str(executed), cwd=project)
        rendered = next((qdir / "results").glob("*.md")).read_text()
        assert "Mean value: -0.021" in rendered

        # every stage is on the record
        log = (qdir / "log.md").read_text()
        for stage in ("asked", "identify", "notebook", "result"):
            assert stage in log

    def test_the_index_is_rebuildable_from_the_wiki_alone(self, project):
        cb("index", cwd=project)
        db = project / ".cb" / "index.duckdb"
        assert db.exists()
        db.unlink()  # derived and disposable, by design
        cb("index", cwd=project)
        assert "q-0001" in cb("sql", "SELECT id FROM questions", cwd=project)

    def test_gaps_reports_the_unobserved_node(self, project):
        cb("index", cwd=project)
        assert "sales_rep_effort" in cb("gaps", cwd=project)

    def test_search_finds_a_past_interview(self, project):
        cb("index", cwd=project)
        assert "q-0001" in cb("find", "eligibility rule", cwd=project)


def test_init_creates_a_working_project(tmp_path):
    cb("init", str(tmp_path / "new"), cwd=tmp_path)
    root = tmp_path / "new"
    assert (root / "wiki" / "graph").is_dir()
    assert ".cb/" in (root / ".gitignore").read_text()
    assert "✓ clean" in cb("doctor", cwd=root)
