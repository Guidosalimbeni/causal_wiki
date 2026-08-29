"""The identification verdict.

`design_alternative` is required whenever the verdict is not IDENTIFIED. A
refusal that does not say what design would work is not a refusal, it is a
dead end — and dead ends are the failure mode this tool exists to avoid. The
schema makes writing one impossible.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, model_validator


class Verdict(str, Enum):
    IDENTIFIED = "IDENTIFIED"
    """A criterion over observed variables yields the effect."""

    NO_CRITERION_FOUND = "NO_CRITERION_FOUND"
    """No backdoor, frontdoor or IV strategy exists over the observed nodes.

    Deliberately not called "unidentifiable": DoWhy's search is sound but we do
    not claim completeness, so this says what we know and no more.
    """

    NO_DIRECTED_PATH = "NO_DIRECTED_PATH"
    """The graph says the treatment cannot affect the outcome at all."""

    NEEDS_EXPANSION = "NEEDS_EXPANSION"
    """An endpoint is defined arithmetically; the question must be re-posed."""


class Strategy(BaseModel):
    kind: str
    variables: list[str] = Field(default_factory=list)
    assumptions: dict[str, str] = Field(default_factory=dict)
    note: str = ""


class Report(BaseModel):
    question_id: str
    treatment: list[str]
    outcome: list[str]
    graph: str | None = None
    verdict: Verdict

    strategies: list[Strategy] = Field(default_factory=list)
    blocking_nodes: list[str] = Field(default_factory=list)
    design_alternative: str = ""

    provisional: bool = False
    unconfirmed_edges: list[str] = Field(default_factory=list)

    observed: list[str] = Field(default_factory=list)
    unobserved: list[str] = Field(default_factory=list)
    expansion: dict[str, list[str]] = Field(default_factory=dict)
    discarded_strategies: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    dowhy_version: str = ""

    @model_validator(mode="after")
    def _refusal_must_propose_a_design(self) -> "Report":
        if self.verdict is not Verdict.IDENTIFIED and not self.design_alternative.strip():
            raise ValueError(
                f"verdict {self.verdict.value} requires a non-empty design_alternative: "
                "a refusal must always say what design would work instead"
            )
        return self

    @property
    def identified(self) -> bool:
        return self.verdict is Verdict.IDENTIFIED

    def save(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
        return path

    def to_markdown(self) -> str:
        icon = "✅" if self.identified else "⛔"
        lines = [
            f"# {icon} Identification — {self.question_id}",
            "",
            f"**Verdict:** `{self.verdict.value}`"
            + ("  _(provisional)_" if self.provisional else ""),
            "",
            f"- **Treatment:** {', '.join(self.treatment) or '—'}",
            f"- **Outcome:** {', '.join(self.outcome) or '—'}",
        ]
        if self.graph:
            lines.append(f"- **Graph:** {self.graph}")
        if self.unobserved:
            lines.append(f"- **Unobserved in scope:** {', '.join(self.unobserved)}")
        lines.append("")

        if self.strategies:
            lines += ["## Strategies", ""]
            for s in self.strategies:
                variables = ", ".join(f"`{v}`" for v in s.variables) or "—"
                lines.append(f"### {s.kind}")
                lines.append(f"- Variables: {variables}")
                if s.note:
                    lines.append(f"- {s.note}")
                for k, v in s.assumptions.items():
                    lines.append(f"- _{k}_: {v}")
                lines.append("")

        if self.blocking_nodes:
            lines += [
                "## What blocks identification",
                "",
                *(f"- `{n}` — unobserved, on a path that cannot be blocked" for n in self.blocking_nodes),
                "",
            ]

        if self.discarded_strategies:
            lines += [
                "## Discarded",
                "",
                *(f"- {d}" for d in self.discarded_strategies),
                "",
            ]

        if self.design_alternative:
            lines += ["## What design would work", "", self.design_alternative, ""]

        if self.provisional:
            lines += [
                "## Unconfirmed edges on the relevant paths",
                "",
                "This verdict rests on edges nobody has confirmed yet:",
                "",
                *(f"- {e}" for e in self.unconfirmed_edges),
                "",
            ]

        if self.notes:
            lines += ["## Notes", "", *(f"- {n}" for n in self.notes), ""]

        return "\n".join(lines)
