"""`wiki/methods/` — what this company estimates with, and how it had to be bent.

The textbook is in the model already. What is tested here is the local record:
that a `method:` string on a question finds its note, that the note lists what
used it, and that a method used with nothing written down gets reported.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from cb.config import Config
from cb.wiki.methods import Method, load, match, tokens

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


def m(id_, *aliases):
    return Method(id=id_, title=id_, aliases=list(aliases))


class TestMatching:
    def test_punctuation_carries_no_meaning(self):
        assert tokens("backdoor.propensity_score_weighting") == [
            "backdoor", "propensity", "score", "weighting"
        ]

    def test_a_dowhy_string_finds_its_note(self):
        notes = [m("propensity-score-weighting")]
        assert match(notes, "backdoor.propensity_score_weighting").id == (
            "propensity-score-weighting"
        )

    def test_an_alias_matches(self):
        notes = [m("iv", "instrumental variables", "2sls")]
        assert match(notes, "2SLS on the rep roster").id == "iv"

    def test_a_short_id_is_not_matched_inside_a_longer_word(self):
        """`iv` must be a word of its own, or every note matches everything."""
        assert match([m("iv")], "driver-level regression") is None

    def test_an_unwritten_method_matches_nothing(self):
        assert match([m("propensity-score-weighting")], "difference in differences") is None

    def test_the_most_specific_note_wins(self):
        notes = [m("weighting"), m("propensity-score-weighting")]
        assert match(notes, "backdoor.propensity_score_weighting").id == (
            "propensity-score-weighting"
        )

    def test_a_question_with_no_method_matches_nothing(self):
        assert match([m("iv")], "") is None

    def test_notes_load_with_their_aliases(self, project):
        notes = load(Config(root=project))
        psw = next(n for n in notes if n.id == "propensity-score-weighting")
        assert "ipw" in psw.aliases


class TestTheFolder:
    def test_init_creates_it(self, tmp_path):
        cb("init", str(tmp_path / "new"), cwd=tmp_path)
        assert (tmp_path / "new" / "wiki" / "methods").is_dir()

    def test_notes_are_searchable(self, project):
        cb("index", cwd=project)
        assert "propensity" in cb("find", "trimming overlap threshold", cwd=project)

    def test_the_context_pack_lists_them(self, project):
        out = cb("context", "q-0001", cwd=project)
        assert "Methods used here" in out
        assert "wiki/methods/propensity-score-weighting.md" in out


class TestUsage:
    def test_cb_methods_counts_what_used_each_note(self, project):
        out = cb("methods", cwd=project)
        assert "propensity-score-weighting" in out and "q-0001" in out

    def test_a_method_with_no_note_is_reported(self, project):
        qfile = next(project.glob("questions/q-0001*")) / "question.md"
        qfile.write_text(
            qfile.read_text().replace(
                "method: backdoor.propensity_score_weighting",
                "method: difference_in_differences",
            )
        )
        out = cb("methods", cwd=project)
        assert "Used but never written up" in out
        assert "difference_in_differences" in out

    def test_and_shows_up_as_a_gap(self, project):
        qfile = next(project.glob("questions/q-0001*")) / "question.md"
        qfile.write_text(
            qfile.read_text().replace(
                "method: backdoor.propensity_score_weighting",
                "method: difference_in_differences",
            )
        )
        cb("index", cwd=project)
        out = cb("gaps", "--kind", "method-without-a-note", cwd=project)
        assert "difference_in_differences" in out

    def test_a_written_up_method_is_not_a_gap(self, project):
        cb("index", cwd=project)
        assert "no gaps found" in cb("gaps", "--kind", "method-without-a-note", cwd=project)


class TestMethodBacklinks:
    def test_the_note_lists_what_used_it(self, project):
        cb("index", cwd=project)
        text = (project / "wiki" / "methods" / "propensity-score-weighting.md").read_text()
        assert "## Questions that used this" in text
        assert "q-0001" in text
        assert "backdoor.propensity_score_weighting" in text.split("## Questions that used")[1]

    def test_the_human_prose_survives(self, project):
        cb("index", cwd=project)
        text = (project / "wiki" / "methods" / "propensity-score-weighting.md").read_text()
        assert "Trim on overlap before estimating" in text

    def test_regenerating_changes_nothing(self, project):
        cb("index", cwd=project)
        note = project / "wiki" / "methods" / "propensity-score-weighting.md"
        before = note.read_text()
        cb("index", cwd=project)
        assert note.read_text() == before

    def test_the_block_goes_when_nothing_uses_it(self, project):
        cb("index", cwd=project)
        qfile = next(project.glob("questions/q-0001*")) / "question.md"
        qfile.write_text(
            qfile.read_text().replace(
                "method: backdoor.propensity_score_weighting", "method: 2sls"
            )
        )
        cb("index", cwd=project)
        text = (project / "wiki" / "methods" / "propensity-score-weighting.md").read_text()
        assert "Questions that used this" not in text


class TestStandingContext:
    def test_init_writes_claude_md(self, tmp_path):
        cb("init", str(tmp_path / "new"), cwd=tmp_path)
        text = (tmp_path / "new" / "CLAUDE.md").read_text()
        assert "causal analyst" in text

    def test_doctor_notices_when_it_is_missing(self, project):
        (project / "CLAUDE.md").unlink()
        assert "no-standing-context" in cb("doctor", cwd=project)

    def test_sync_writes_a_missing_one_back(self, project):
        (project / "CLAUDE.md").unlink()
        cb("sync", cwd=project)
        assert (project / "CLAUDE.md").exists()
        assert "✓ clean" in cb("doctor", cwd=project)

    def test_sync_never_takes_back_an_edited_one(self, project):
        """It is the project's own context, and `sync --force` must not reclaim it."""
        (project / "CLAUDE.md").write_text("my own house rules\n")
        cb("sync", "--force", cwd=project)
        assert (project / "CLAUDE.md").read_text() == "my own house rules\n"
