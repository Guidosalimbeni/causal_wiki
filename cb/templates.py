"""Shipping the judgement layer.

`cb` is deterministic Python, but on its own it is only half the tool: the
interview, the routing rules and the slash commands are what make it useful.
Those are markdown, so they travel as package data and get written into a
project by `cb init`.

Nothing here ever overwrites a file you have edited. The skills are meant to be
changed — that is the point of them being prose — so a file that differs from
the template is left exactly as it is and reported, not clobbered.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path

SKILLS = "skills"
COMMANDS = "commands"
PROJECT = "project"

# Where each set of templates lands, relative to the project root.
DESTINATIONS = {
    SKILLS: Path("skills"),
    COMMANDS: Path(".claude") / "commands" / "cb",
    PROJECT: Path("."),
}

# `cb sync` refreshes the judgement layer after an upgrade. It leaves the
# scaffold alone: CLAUDE.md is a project's own always-on context, so a later
# `sync --force` must not be able to take it back.
SYNCED = [SKILLS, COMMANDS]


@dataclass
class Written:
    path: Path
    action: str  # "created" | "unchanged" | "kept" | "overwritten"

    def __str__(self) -> str:
        note = {
            "created": "",
            "unchanged": "  (already current)",
            "kept": "  (yours differs — left alone; --force to replace)",
            "overwritten": "  (replaced)",
        }[self.action]
        return f"{self.action:12s} {self.path}{note}"


def _templates(group: str) -> list[tuple[str, str]]:
    root = resources.files("cb").joinpath("templates", group)
    return sorted(
        (entry.name, entry.read_text(encoding="utf-8"))
        for entry in root.iterdir()
        if entry.name.endswith(".md")
    )


def materialise(root: Path, force: bool = False, groups: list[str] | None = None) -> list[Written]:
    """Write the shipped skills, slash commands and scaffold into a project."""
    out: list[Written] = []
    for group in groups or list(DESTINATIONS):
        target_dir = Path(root) / DESTINATIONS[group]
        target_dir.mkdir(parents=True, exist_ok=True)
        for name, content in _templates(group):
            target = target_dir / name
            if not target.exists():
                action = "created"
            elif target.read_text(encoding="utf-8") == content:
                action = "unchanged"
            elif force:
                action = "overwritten"
            else:
                # An edited skill is the user's work, not stale scaffolding.
                out.append(Written(path=target.relative_to(root), action="kept"))
                continue
            target.write_text(content, encoding="utf-8")
            out.append(Written(path=target.relative_to(root), action=action))
    return out
