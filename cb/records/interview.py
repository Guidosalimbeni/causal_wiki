"""The interview record.

Not a transcript to be filed away: future questions search this, so a good
interview makes the next one shorter. Kept deliberately permissive — the
interview is judgement, and a rigid schema would turn it into a fixed menu of
question types. Unknown keys are preserved.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class Turn(BaseModel):
    model_config = ConfigDict(extra="allow")
    asked: str = ""
    answered: str = ""
    established: str = ""


class ProposedEdge(BaseModel):
    model_config = ConfigDict(extra="allow")
    source: str
    target: str
    kind: str = "causal"
    reason: str = ""
    confirmed: bool = False


class Interview(BaseModel):
    model_config = ConfigDict(extra="allow")

    question_id: str
    posed_as: str = ""
    graph: str | None = None
    treatment: list[str] = Field(default_factory=list)
    outcome: list[str] = Field(default_factory=list)
    population: str = ""
    period: str = ""

    turns: list[Turn] = Field(default_factory=list)
    edges: list[ProposedEdge] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    wiki_gaps: list[str] = Field(default_factory=list)

    ready: bool = False
    """Whether the situation is understood well enough to proceed."""

    def searchable_text(self) -> str:
        """Flattened for full-text search."""
        parts = [self.posed_as, self.population, self.period]
        for t in self.turns:
            parts += [t.asked, t.answered, t.established]
        parts += self.assumptions + self.open_questions + self.wiki_gaps
        parts += [f"{e.source} -> {e.target}: {e.reason}" for e in self.edges]
        return "\n".join(p for p in parts if p)

    def save(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(
                self.model_dump(mode="json"), sort_keys=False, allow_unicode=True, width=88
            ),
            encoding="utf-8",
        )
        return path


def load(path: Path) -> Interview:
    data: dict[str, Any] = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return Interview(**data)
