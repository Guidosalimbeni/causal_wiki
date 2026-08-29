"""The judgement layer ships with the library and never clobbers your edits."""

from __future__ import annotations

from pathlib import Path

import pytest

from cb import templates
from cb.config import Config

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def project(tmp_path):
    cfg = Config(root=tmp_path)
    for d in cfg.dirs():
        d.mkdir(parents=True, exist_ok=True)
    return tmp_path


class TestMaterialise:
    def test_it_writes_the_skills_and_the_commands(self, project):
        templates.materialise(project)
        assert (project / "skills" / "interview.md").exists()
        assert (project / ".claude" / "commands" / "cb" / "ask.md").exists()

    def test_everything_shipped_lands(self, project):
        written = templates.materialise(project)
        assert {w.action for w in written} == {"created"}
        assert len(written) == len(templates._templates("skills")) + len(
            templates._templates("commands")
        )

    def test_running_twice_changes_nothing(self, project):
        templates.materialise(project)
        again = templates.materialise(project)
        assert {w.action for w in again} == {"unchanged"}

    def test_an_edited_skill_is_kept(self, project):
        """The skills are meant to be changed — that is why they are prose."""
        templates.materialise(project)
        skill = project / "skills" / "interview.md"
        skill.write_text("my own house rules\n")

        written = templates.materialise(project)

        assert skill.read_text() == "my own house rules\n"
        assert any(w.action == "kept" and w.path.name == "interview.md" for w in written)

    def test_force_replaces_an_edited_skill(self, project):
        templates.materialise(project)
        skill = project / "skills" / "interview.md"
        skill.write_text("my own house rules\n")

        written = templates.materialise(project, force=True)

        assert "The interview" in skill.read_text()
        assert any(w.action == "overwritten" for w in written)

    def test_force_does_not_touch_files_that_already_match(self, project):
        templates.materialise(project)
        written = templates.materialise(project, force=True)
        assert all(w.action == "unchanged" for w in written)

    def test_a_single_group_can_be_written(self, project):
        templates.materialise(project, groups=[templates.SKILLS])
        assert (project / "skills" / "interview.md").exists()
        assert not (project / ".claude").exists()

    def test_templates_are_readable_as_package_data(self):
        """Guards against a wheel that ships the code but not the markdown."""
        for group in (templates.SKILLS, templates.COMMANDS):
            found = templates._templates(group)
            assert found, f"no {group} templates found in the installed package"
            assert all(text.strip() for _, text in found)


class TestNoDrift:
    """This repo's own copies are materialised from the templates.

    If you edit one in place, the shipped version silently falls behind and
    every new project gets the stale one. Edit `cb/templates/` instead.
    """

    @pytest.mark.parametrize("group", [templates.SKILLS, templates.COMMANDS])
    def test_repo_copies_match_the_shipped_templates(self, group):
        destination = REPO / templates.DESTINATIONS[group]
        for name, content in templates._templates(group):
            local = destination / name
            assert local.exists(), f"{local} is missing — run `cb sync`"
            assert local.read_text(encoding="utf-8") == content, (
                f"{local} has drifted from cb/templates/{group}/{name}. "
                f"Edit the template, then run `cb sync --force`."
            )

    @pytest.mark.parametrize("group", [templates.SKILLS, templates.COMMANDS])
    def test_no_extra_files_in_the_repo_copies(self, group):
        shipped = {name for name, _ in templates._templates(group)}
        local = {p.name for p in (REPO / templates.DESTINATIONS[group]).glob("*.md")}
        assert local == shipped, (
            f"{local ^ shipped} exists in one place but not the other; "
            f"move it into cb/templates/{group}/ so it ships."
        )
