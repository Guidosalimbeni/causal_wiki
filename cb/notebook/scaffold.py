"""Notebook scaffolding — the skeleton only.

Method choice is judgement and stays in a skill. What the code owns is the
frame: which question this belongs to, what identification actually licensed,
and where the result goes when it comes back. Baking the verdict into the
notebook means the analyst cannot run it without seeing what was assumed.
"""

from __future__ import annotations

from pathlib import Path

HEADER = """# {qid} — {question}

**Identification:** `{verdict}`{provisional}

{strategy_block}

> Run this in your own environment, where the data is. Bring it back with
> `cb result add {qid} <path-to-executed-notebook>`.
"""

PARAMS = """# --- parameters -------------------------------------------------------
QUESTION_ID = {qid!r}
TREATMENT = {treatment!r}
OUTCOME = {outcome!r}
ADJUSTMENT_SET = {adjustment!r}   # from identification, not from judgement
STRATEGY = {strategy!r}
"""

LOAD = '''# --- load ------------------------------------------------------------
# Point this at your warehouse. The wiki records where these tables live.
import pandas as pd

df = None  # TODO: load the analysis frame
'''

CHECKS = '''# --- sanity checks before estimating ---------------------------------
# Cheap checks that catch the usual wrong answers.
assert df is not None, "load the data first"
print("rows:", len(df))
print(df[[*TREATMENT, *OUTCOME, *ADJUSTMENT_SET]].isna().mean().rename("missing_frac"))
print(df[TREATMENT[0]].value_counts(dropna=False))
'''

FOOTER = '''# --- what to bring back ----------------------------------------------
# Print whatever the conversation needs to continue: the estimate, its
# uncertainty, and anything that surprised you. A run that failed is still
# worth bringing back.
'''


def _strategy_block(report) -> str:
    if report is None:
        return "_No identification report attached._"
    if not report.identified:
        return (
            f"**This question was refused.** {report.design_alternative}\n\n"
            "> This notebook is a scratchpad for exploring the refusal — it must not be "
            "> used to produce a causal estimate."
        )
    # The verb matters. A frontdoor mediator is used in two stages, never
    # adjusted for — saying "adjust for" here would invite the precise mistake
    # the wiki records as a trap.
    verb = {
        "backdoor": "adjust for",
        "general_adjustment": "adjust for",
        "frontdoor": "estimate in two stages through",
        "iv": "instrument with",
    }
    lines = []
    for s in report.strategies:
        variables = ", ".join(f"`{v}`" for v in s.variables) or "_none needed_"
        lines.append(f"- **{s.kind}** — {verb.get(s.kind, 'use')} {variables}. {s.note}")
    return "\n".join(lines)


def build(question, report=None, name: str | None = None, cells: list[str] | None = None) -> Path:
    """Write a notebook skeleton into the question's notebooks/ directory."""
    import nbformat as nbf

    strategy = report.strategies[0] if (report and report.strategies) else None
    adjustment = strategy.variables if strategy else []

    nb = nbf.v4.new_notebook()
    nb.cells = [
        nbf.v4.new_markdown_cell(
            HEADER.format(
                qid=question.id,
                question=question.question,
                verdict=report.verdict.value if report else "not run",
                provisional=" _(provisional)_" if (report and report.provisional) else "",
                strategy_block=_strategy_block(report),
            )
        ),
        nbf.v4.new_code_cell(
            PARAMS.format(
                qid=question.id,
                treatment=question.treatment,
                outcome=question.outcome,
                adjustment=adjustment,
                strategy=strategy.kind if strategy else None,
            )
        ),
        nbf.v4.new_code_cell(LOAD),
        nbf.v4.new_code_cell(CHECKS),
        nbf.v4.new_markdown_cell("## Estimation"),
        *[nbf.v4.new_code_cell(c) for c in (cells or ["# TODO: estimate\n"])],
        nbf.v4.new_markdown_cell("## Result"),
        nbf.v4.new_code_cell(FOOTER),
    ]

    question.notebooks_dir.mkdir(parents=True, exist_ok=True)
    if name is None:
        n = len(list(question.notebooks_dir.glob("nb-*.ipynb"))) + 1
        name = f"nb-{n:02d}.ipynb"
    path = question.notebooks_dir / name
    nbf.write(nb, path)
    question.stamp("notebook", f"scaffolded {name}")
    return path


# -- the experiment ----------------------------------------------------------
#
# Randomisation is not the consolation prize for a failed identification. It is
# the design that needs no untestable assumption at all, and it stays on the
# table whatever the verdict was: as the answer when nothing observational
# recovers the effect, and as the confirmation when something did.

DESIGN_HEADER = """# {qid} — experiment design

**Question:** {question}

**Identification:** `{verdict}` — {stance}

{design_block}

## Before this is a design

Fill in the parameters below *with the analyst*, not alone. The unit of
randomisation, the exposure window and the guardrails are business decisions,
and getting them wrong is not recoverable after the fact.

Read `wiki/methods/` first — how this company randomises, what its traffic
supports, and what went wrong last time are already written down there.

> When it has run, write it up in `wiki/experiments/<slug>.md`, then set
> `experiment:` and `design_status: ran` on `questions/{qid}/question.md`.
"""

DESIGN_PARAMS = """# --- the design -------------------------------------------------------
QUESTION_ID = {qid!r}
TREATMENT = {treatment!r}          # what gets randomised
OUTCOME = {outcome!r}              # the primary metric, and only one

UNIT = "TODO"                # booking? account? rep? the unit that gets assigned
ARMS = {{"control": 0.5, "treatment": 0.5}}
POPULATION = "TODO"          # who is eligible to be randomised, stated exactly
EXPOSURE_WINDOW = "TODO"     # how long assignment runs
OUTCOME_WINDOW = "TODO"      # how long after exposure the outcome is measured

MDE = None                   # smallest effect worth detecting, in outcome units
ALPHA, POWER = 0.05, 0.8
GUARDRAILS = []              # metrics that must not move, checked as decision rules

# Clustering is the usual way a test overstates its own precision: if the unit
# assigned is not the unit measured — reps assigned, bookings measured — the
# analysis has to account for it and the sample size has to pay for it.
CLUSTERED = None             # True if assignment and measurement differ
"""

DESIGN_POWER = '''# --- how much traffic this needs --------------------------------------
# Sample size first. A test that cannot detect the effect anyone cares about
# wastes the exposure and returns a null nobody can interpret.
import numpy as np
from scipy import stats

BASELINE = None   # current mean/rate of OUTCOME in POPULATION

def n_per_arm(baseline, mde, alpha=ALPHA, power=POWER, binary=True):
    z_a = stats.norm.ppf(1 - alpha / 2)
    z_b = stats.norm.ppf(power)
    var = baseline * (1 - baseline) if binary else baseline
    return int(np.ceil(2 * var * (z_a + z_b) ** 2 / mde**2))

# print(n_per_arm(BASELINE, MDE), "units per arm")
# Then: how long does that take at current volume? If the answer is longer than
# the business will wait, say so now and negotiate the MDE, not later.
'''

DESIGN_ASSIGNMENT = '''# --- assignment, and the checks that catch a broken test ---------------
# Deterministic hashing, so the assignment is reproducible and auditable.
import hashlib

def assign(unit_id, salt=QUESTION_ID):
    h = hashlib.sha256(f"{salt}:{unit_id}".encode()).hexdigest()
    return "treatment" if int(h[:8], 16) / 0xFFFFFFFF < ARMS["treatment"] else "control"

# Checks to run on live data before trusting any result:
#   1. Sample ratio mismatch — arm counts against ARMS. A failed SRM invalidates
#      the test; it does not "wash out with more data".
#   2. Balance on the pre-treatment variables the wiki says decide assignment.
#   3. Any rule that could override randomisation. If the business can hand-pick
#      units out of the treatment arm, the design is not randomised.
'''

DESIGN_PLAN = '''# --- the analysis, written before the data exists ----------------------
# Pre-registering this is the point. Deciding how to analyse after seeing the
# result is how a null becomes a finding.
#
#   - Estimator: difference in means on the primary metric, intention-to-treat.
#   - Analyse everyone as assigned, including units that never saw the treatment.
#     Dropping non-compliers reintroduces exactly the selection the design removed.
#   - Covariate adjustment for precision only, on pre-treatment variables named
#     in advance. Never chosen after looking.
#   - One primary metric and one decision rule. Guardrails are checked, not ranked.
#   - Stopping rule, stated now: fixed horizon, or a sequential test that pays
#     for the peeking.
'''

DESIGN_FOOTER = '''# --- what to bring back -----------------------------------------------
# The estimate with its interval, the arm counts, the SRM and balance checks,
# and anything that made the design fail to run as written. A test that broke is
# worth as much as one that worked, and only if it is recorded.
'''


def design(question, report=None, name: str | None = None) -> Path:
    """Scaffold an experiment design for a question.

    Available whatever the verdict was. "Give me the design and a notebook" is
    a legitimate request even when the effect is identifiable — never a dead end.
    """
    import nbformat as nbf

    if report is None:
        stance = "no identification report yet; the design stands on its own."
        block = ""
    elif report.identified:
        stance = (
            "an observational estimate is available, so this experiment is for "
            "confirmation — the strongest thing that can be said about a finding "
            "is that two designs with different assumptions agreed."
        )
        block = (
            "## Why run it anyway\n\n"
            "The observational answer rests on the adjustment argument being right. "
            "This does not. Where they agree, the finding is solid; where they "
            "disagree, the disagreement is itself the finding."
        )
    else:
        stance = "the effect is not recoverable from the data as it stands, so this is the answer."
        block = f"## What identification said\n\n{report.design_alternative}"

    nb = nbf.v4.new_notebook()
    nb.cells = [
        nbf.v4.new_markdown_cell(
            DESIGN_HEADER.format(
                qid=question.id,
                question=question.question,
                verdict=report.verdict.value if report else "not run",
                stance=stance,
                design_block=block,
            )
        ),
        nbf.v4.new_code_cell(
            DESIGN_PARAMS.format(
                qid=question.id, treatment=question.treatment, outcome=question.outcome
            )
        ),
        nbf.v4.new_markdown_cell("## Power"),
        nbf.v4.new_code_cell(DESIGN_POWER),
        nbf.v4.new_markdown_cell("## Assignment"),
        nbf.v4.new_code_cell(DESIGN_ASSIGNMENT),
        nbf.v4.new_markdown_cell("## Pre-registered analysis"),
        nbf.v4.new_code_cell(DESIGN_PLAN),
        nbf.v4.new_markdown_cell("## When it comes back"),
        nbf.v4.new_code_cell(DESIGN_FOOTER),
    ]

    question.notebooks_dir.mkdir(parents=True, exist_ok=True)
    if name is None:
        n = len(list(question.notebooks_dir.glob("design-*.ipynb"))) + 1
        name = f"design-{n:02d}.ipynb"
    path = question.notebooks_dir / name
    nbf.write(nb, path)
    question.stamp("design", f"scaffolded {name}")
    return path
