"""Where things live.

A cb project is any directory containing a `wiki/` folder. Paths are resolved
by walking up from the working directory, so cb works from anywhere inside a
project the way git does.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

MARKERS = ("cb.toml", "wiki")


@dataclass(frozen=True)
class Config:
    root: Path

    @property
    def wiki(self) -> Path:
        return self.root / "wiki"

    @property
    def graph_dir(self) -> Path:
        return self.wiki / "graph"

    @property
    def data_dir(self) -> Path:
        return self.wiki / "data"

    @property
    def tables_dir(self) -> Path:
        return self.data_dir / "tables"

    @property
    def experiments_dir(self) -> Path:
        return self.wiki / "experiments"

    @property
    def process_dir(self) -> Path:
        return self.wiki / "process"

    @property
    def methods_dir(self) -> Path:
        """How this company estimates things. Not the textbook — IV and DiD are
        in the model's training data already. What is written here is the local
        tailoring: which instrument held up, which window, which cohort, and
        what went wrong last time."""
        return self.wiki / "methods"

    @property
    def traps_dir(self) -> Path:
        return self.wiki / "traps"

    @property
    def rules_dir(self) -> Path:
        """Business rules and policies. A rule that decides who gets treated IS
        the confounding, and is usually written down nowhere else."""
        return self.wiki / "rules"

    @property
    def questions(self) -> Path:
        return self.root / "questions"

    @property
    def raw(self) -> Path:
        return self.root / "raw"

    @property
    def skills(self) -> Path:
        return self.root / "skills"

    @property
    def state_dir(self) -> Path:
        return self.root / ".cb"

    @property
    def db(self) -> Path:
        """Derived, disposable, gitignored. Never a source of truth."""
        return self.state_dir / "index.duckdb"

    def dirs(self) -> list[Path]:
        return [
            self.graph_dir,
            self.tables_dir,
            self.process_dir,
            self.methods_dir,
            self.experiments_dir,
            self.traps_dir,
            self.rules_dir,
            self.questions,
            self.raw,
            self.skills,
        ]


def find_root(start: Path | None = None) -> Path:
    current = Path(start or os.getcwd()).resolve()
    for candidate in [current, *current.parents]:
        if any((candidate / m).exists() for m in MARKERS):
            return candidate
    raise FileNotFoundError(
        "not inside a cb project (no wiki/ directory found in this directory or any parent). "
        "Run `cb init` to create one."
    )


def load(start: Path | None = None) -> Config:
    return Config(root=find_root(start))
