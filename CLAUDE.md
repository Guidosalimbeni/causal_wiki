# cb — working on the tool itself

A companion for causal analysis inside a company: deterministic Python plus a
prose judgement layer. No LLM calls, no API key. [README.md](README.md) has the
design and the reasoning; this file is only what you need before touching code.

## The two-copy rule

`skills/*.md` and `.claude/commands/cb/*.md` in this repo are **materialised
copies** of `cb/templates/`. Edit the template, then `cb sync --force`. Editing a
copy in place means every new project gets the stale version — `tests/test_templates.py`
fails on the drift.

`cb/templates/project/CLAUDE.md` is the CLAUDE.md written into a *user's* project.
It is not this file, and `cb sync` never touches it.

## Layout

- `cb/` — identification, the parser, records, the notebook scaffold, validation, the index
- `cb/templates/` — the shipped judgement layer, written out by `cb init`
- `examples/toy-company/` — a complete worked project; `cb doctor && cb identify q-0001` there

## Commands

`pip install -e ".[dev]"` · `pytest`

## Rules that do not bend

- Refuse when identification is not possible, and always say what design would work.
- Never dead-end.
- Never change a confirmed causal edge without asking.
