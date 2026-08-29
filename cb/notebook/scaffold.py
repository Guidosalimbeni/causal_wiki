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
