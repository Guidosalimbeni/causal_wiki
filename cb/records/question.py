"""The question record. Every stage hangs off the id.

    questions/q-0007-addon-churn/
        question.md          frontmatter + the question as it was asked
        interview.yaml       stage three
        identification.json  stage three-and-a-half, plus a rendered .md
        notebooks/           stage four
        results/             stage five
        log.md               what happened, when

Abandoning a question requires a reason, enforced here rather than by
convention: the abandoned questions and the failed notebooks are the useful
ones, and a system that only records successes never learns from them.
"""

from __future__ import annotations

import datetime as _dt
import re
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from ..wiki import frontmatter

ID_RE = re.compile(r"^q-(\d{4})")
# `- `2026-08-29T15:45:14` **stage**` — the line `stamp()` writes.
_LOG_STAMP = re.compile(r"^-\s+`(?P<when>\d{4}-\d{2}-\d{2}[T \d:]*)`")


class Status(str, Enum):
    DRAFT = "draft"
    INTERVIEWING = "interviewing"
    IDENTIFIED = "identified"
    REFUSED = "refused"
    NOTEBOOK = "notebook"
    ANALYSING = "analysing"
    CONCLUDED = "concluded"
    ABANDONED = "abandoned"


TERMINAL = {Status.CONCLUDED, Status.ABANDONED}


class DesignStatus(str, Enum):
    """Where a proposed experiment stands.

    A design named in a refusal and then forgotten is the same dead end the
    refusal was supposed to avoid, one step further along. Tracking it is what
    turns "randomise it" from a sentence into work someone can pick up.
    """

    PROPOSED = "proposed"
    AGREED = "agreed"
    RUNNING = "running"
    RAN = "ran"
    DECLINED = "declined"


OPEN_DESIGNS = {DesignStatus.PROPOSED, DesignStatus.AGREED, DesignStatus.RUNNING}


def today() -> str:
    return _dt.date.today().isoformat()


def slugify(text: str, limit: int = 5) -> str:
    words = re.findall(r"[a-z0-9]+", text.lower())
    # Prepositions are deliberately absent: "add-on" tokenises to add + on, and
    # dropping "on" would slug it as "add".
    skip = {"the", "a", "an", "is", "are", "do", "does", "did", "we", "what", "how", "why"}
    kept = [w for w in words if w not in skip] or words
    return "-".join(kept[:limit]) or "question"


class Question(BaseModel):
    id: str
    slug: str = ""
    question: str
    asked_by: str = ""
    asked_on: str = Field(default_factory=today)
    status: Status = Status.DRAFT

    graph: str | None = None
    treatment: list[str] = Field(default_factory=list)
    outcome: list[str] = Field(default_factory=list)

    verdict: str | None = None
    method: str | None = None
    treatment_kind: str | None = None

    # An experiment: proposed instead of an answer, or alongside one.
    design: str | None = None
    design_status: DesignStatus | None = None
    experiment: str | None = None
    effect: str | None = None
    finding: str | None = None
    abandoned_reason: str | None = None

    body: str = ""
    dir: Path | None = None

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def _a_design_status_needs_a_design(self) -> "Question":
        if self.design_status and not (self.design or "").strip():
            raise ValueError(
                f"design_status '{self.design_status.value}' with no design — "
                "say what would be run, not just that something would be"
            )
        if self.design_status is DesignStatus.RAN and not (self.experiment or "").strip():
            raise ValueError(
                "design_status 'ran' requires experiment: the slug of the "
                "wiki/experiments/ note recording what it found"
            )
        return self

    @model_validator(mode="after")
    def _abandoning_requires_a_reason(self) -> "Question":
        if self.status is Status.ABANDONED and not (self.abandoned_reason or "").strip():
            raise ValueError(
                "status 'abandoned' requires abandoned_reason — "
                "the questions we drop are the ones worth learning from"
            )
        return self

    # -- paths ---------------------------------------------------------------

    @property
    def path(self) -> Path:
        return Path(self.dir) / "question.md"  # type: ignore[arg-type]

    @property
    def interview_path(self) -> Path:
        return Path(self.dir) / "interview.yaml"  # type: ignore[arg-type]

    @property
    def identification_path(self) -> Path:
        return Path(self.dir) / "identification.json"  # type: ignore[arg-type]

    @property
    def notebooks_dir(self) -> Path:
        return Path(self.dir) / "notebooks"  # type: ignore[arg-type]

    @property
    def results_dir(self) -> Path:
        return Path(self.dir) / "results"  # type: ignore[arg-type]

    @property
    def log_path(self) -> Path:
        return Path(self.dir) / "log.md"  # type: ignore[arg-type]

    # -- ageing --------------------------------------------------------------

    @property
    def last_activity(self) -> str:
        """When this question was last touched.

        Read from the log rather than the file mtime, which a fresh clone or a
        checkout resets. It is what lets `cb gaps` age a stalled question out
        instead of listing everything still in flight — with several analysts
        asking daily, "not yet concluded" is the normal state, and a gap that
        fires on all of them is one nobody reads.
        """
        path = self.log_path
        if path.exists():
            stamps = [
                m.group("when")
                for m in (
                    _LOG_STAMP.match(line)
                    for line in path.read_text(encoding="utf-8").splitlines()
                )
                if m
            ]
            if stamps:
                return max(stamps)
        return self.asked_on

    @property
    def nodes(self) -> set[str]:
        """The graph nodes this question is about — how relevance is judged."""
        return {n for n in (*self.treatment, *self.outcome) if n}

    # -- io ------------------------------------------------------------------

    def meta(self) -> dict:
        data = self.model_dump(exclude={"body", "dir"}, mode="json")
        return {k: v for k, v in data.items() if v not in (None, [], "")}

    def save(self) -> Path:
        doc = frontmatter.Doc(meta=self.meta(), body=self.body or _default_body(self))
        return doc.save(self.path)

    def stamp(self, stage: str, note: str = "") -> None:
        line = f"- `{_dt.datetime.now().isoformat(timespec='seconds')}` **{stage}**"
        if note:
            line += f" — {note}"
        path = self.log_path
        path.parent.mkdir(parents=True, exist_ok=True)
        header = "" if path.exists() else f"# Log — {self.id}\n\n"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(header + line + "\n")


def _default_body(q: Question) -> str:
    return (
        f"# {q.question}\n\n"
        "## As asked\n\n"
        f"> {q.question}\n\n"
        "## How it should be posed\n\n"
        "_Filled in during the interview._\n\n"
        "## Findings\n\n"
        "_Filled in at stage five._\n"
    )


def load(directory: Path) -> Question:
    directory = Path(directory)
    doc = frontmatter.load(directory / "question.md")
    return Question(**doc.meta, body=doc.body, dir=directory)


def iter_questions(root: Path):
    root = Path(root)
    if not root.exists():
        return
    for directory in sorted(root.iterdir()):
        if directory.is_dir() and (directory / "question.md").exists():
            yield load(directory)


def next_id(root: Path) -> str:
    highest = 0
    for directory in Path(root).glob("q-*"):
        match = ID_RE.match(directory.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"q-{highest + 1:04d}"


def create(root: Path, question: str, asked_by: str = "", graph: str | None = None) -> Question:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    qid = next_id(root)
    slug = slugify(question)
    q = Question(
        id=qid,
        slug=slug,
        question=question.strip(),
        asked_by=asked_by,
        graph=graph,
        dir=root / f"{qid}-{slug}",
    )
    q.notebooks_dir.mkdir(parents=True, exist_ok=True)
    q.results_dir.mkdir(parents=True, exist_ok=True)
    q.save()
    q.stamp("asked", question.strip())
    return q


def find(root: Path, qid: str) -> Question:
    root = Path(root)
    for directory in root.glob(f"{qid}*"):
        if (directory / "question.md").exists():
            return load(directory)
    raise FileNotFoundError(f"no question record for '{qid}' under {root}")
