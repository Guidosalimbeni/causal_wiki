# cb

A companion for causal analysis inside a company. It remembers what has been
learned about that company's data and about which designs actually worked there,
so the tenth question is cheaper to answer than the first.

Python, DuckDB, git, markdown. No API key — `cb` never calls an LLM. It is
driven from Claude Code, where the judgement happens.

## To install for company specific

to install pip install git+https://github.com/Guidosalimbeni/causal_wiki.git

in a folder/repo
then cb init .

## The split

|                                 |                                                                                       |
| ------------------------------- | ------------------------------------------------------------------------------------- |
| **`cb`** — deterministic Python | identification, the parser, the records, the notebook scaffold, validation, the index |
| **`skills/`** — prose           | the interview, routing, critique, proposing edges, choosing methods, writing up       |
| **`.claude/commands/cb/`**      | the actual entry points: `/cb:ingest`, `/cb:ask`, `/cb:resume`, `/cb:gaps`            |
| **`CLAUDE.md`**                 | the project's always-on context: where things are, and the rules that do not bend     |

Both halves ship with the library. `cb init` writes the skills and slash
commands into your project; the shipped copies live in `cb/templates/`.

`cb ask` opens a record and assembles context; it does not conduct the
interview. That happens in the conversation, which is the only place it can.

## The five stages

```
/cb:ingest                     1. collecting — raw/ into the wiki
/cb:ask "<what they asked>"    2. a question arrives
                               3. the interview — the heart of it
                               4. a notebook, run where the data is
cb result add <qid> <nb>       5. it comes back; refine, re-run, or conclude
```

Every question gets an id and all five stages hang off it, in
`questions/q-NNNN-slug/`.

## Install

Into a new, empty repo:

```bash
cd your-repo
python3 -m venv .venv
.venv/bin/pip install /path/to/causal_wiki
.venv/bin/cb init .
```

`cb init` creates the wiki skeleton **and** writes out `CLAUDE.md`, `skills/` and
`.claude/commands/cb/`, so the slash commands work immediately — restart Claude
Code if it was already running, as it discovers commands at startup. It never
overwrites a skill you have edited — the skills are meant to be changed. After
upgrading `cb`, `cb sync` pulls in any new or changed skills and commands, again
leaving your edits alone (`--force` if you want the shipped versions back).
`sync` never touches `CLAUDE.md` — that one is yours the moment it is written.

For work on `cb` itself: `pip install -e ".[dev]"`.

## The wiki

Markdown in git, readable in Obsidian, organised for reading:

```
wiki/
  data/tables/   where things live, columns, joins, filters, causal annotations
  graph/         one file per variable — the causal graph
  rules/         business rules — these decide who gets treated
  process/       how the business actually works, in prose
  methods/       how this company estimates things — the local tailoring
  experiments/   what was tried and what it found
  traps/         mistakes that keep getting made here
```

### `methods/` holds the tailoring, not the textbook

IV, DiD, synthetic control, interrupted time series — the model already knows
all of them, and restating them here would be the least useful thing this wiki
could hold. What is nowhere in its training is how each had to be bent to fit
*this* business: which instrument survived scrutiny, which window the billing
cycle forces, why the obvious cohort definition is unavailable, what broke last
time.

Methods repeat far more than questions do. The same weighting approach comes
back for every treatment gated by an eligibility rule, so the note accretes and
the fourth question to use it is where it gets good.

```bash
cb methods    # what has been used here, how often, and what was never written up
```

`cb index` lists the questions that used each note on the note itself, and
`cb gaps` reports a method used with nothing written down about it. Kept
separate from `experiments/`, which records one thing that was run and what it
found — a claim with a date on it, rather than standing guidance.

### The graph lives in the wiki, one file per node

Obsidian's graph view has no direction and no edge types, so the headings carry
them:

```markdown
---
id: addon_shown
observed: true
measured: at_quote # before or after the treatment
causal_role: treatment
graphs: [addon_uptake] # the only source of graph membership
confirmed_by: guido
---

## Caused by

- [[lead_time_days]] — rule threshold at 60 days <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 -->

## Causes

- [[churn_90d]] — hypothesised

## Computed from

(arithmetic only — never enters the causal graph)
```

Machine fields go in an HTML comment so Obsidian's reading view stays clean.
Declare an edge on either endpoint or both; the parser unions them and
`cb doctor` flags only contradictions.

`## Computed from` is a different kind of edge on purpose. `net_revenue =
revenue x (1 - churn)` is exactly true and says nothing about cause; kept
separate it cannot be certified as a finding.

## Identification

The one step that is code and not judgement. An LLM asked "is this identified?"
is usually right, and _usually_ fails exactly when there is a deadline and
someone wants a number.

```
$ cb identify q-0002
⛔ Identification — q-0002

**Verdict:** `NO_CRITERION_FOUND`
- Unobserved in scope: sales_rep_effort

## What blocks identification
- `sales_rep_effort` — unobserved, on a path that cannot be blocked

## What design would work
`sales_rep_effort` is an unobserved common cause of `rep_call_made` and
`upgrade_purchased`, and no observed set blocks the backdoor path it opens.
1. **Measure `sales_rep_effort`.** …
2. **Randomise `rep_call_made`.** …
```

A refusal exits non-zero and **cannot be serialized without a
`design_alternative`** — the schema enforces it, so a dead end is not
expressible.

Three verdicts beyond `IDENTIFIED`: `NO_CRITERION_FOUND` (no backdoor, frontdoor
or IV strategy over the observed nodes), `NO_DIRECTED_PATH` (the graph says the
treatment cannot affect the outcome), and `NEEDS_EXPANSION` (the outcome is an
accounting identity — re-pose it against the components).

### Two guards around DoWhy

Both verified against dowhy 0.14, both pinned by tests in
[tests/test_identify.py](tests/test_identify.py):

1. **`identify_effect_auto` does not raise on an unidentifiable effect.** It
   returns all-`None` estimands — or, when there is no directed path, an
   `estimands` attribute that is itself `None`. Both shapes are checked.
2. **DoWhy will hand back an estimand that needs an unobserved variable.** On an
   M-bias graph with observed `{Z,T,Y}` it proposes the latent `U1` as an
   instrument, with a full estimand expression. Trusting `estimands['iv'] is not
None` would certify a design requiring a variable we have declared
   unmeasurable — the exact failure this tool exists to prevent. Every strategy
   is filtered against the observed set before it counts.

`NO_CRITERION_FOUND` is deliberately not called "unidentifiable": DoWhy's search
is sound, and we do not claim completeness. (Its ID-algorithm implementation
takes no `observed_nodes` argument and treats every node as measured, so it
cannot supply that proof.)

## Re-import safety

Semantic-layer exports get re-imported. `cb ingest` only ever rewrites the bytes
between markers:

```
<!-- cb:managed name=schema source=raw/semantic-layer.csv sha=ab12cd -->
<!-- /cb:managed -->
```

Everything outside is human territory. A column that vanishes upstream is
**retired, never deleted** — the reason someone marked it a collider outlives
the column. And ingest writes no causal edges at all: that is the fix for the
approval queue that once produced 29 pending items nobody read. The graph gets
drawn in the interview, where the analyst is already answering questions.

## The index

```bash
cb index          # drop and rebuild .cb/index.duckdb from the wiki
cb gaps           # what haven't we looked at?
cb find "..."     # search past interviews, questions, tables, traps
cb sql "SELECT method, verdict, count(*) FROM effects GROUP BY 1,2"
```

Derived, disposable, gitignored, rebuilt from markdown every time. Markdown is
the only thing anyone writes, so the two can never drift. It earns its place
because the wiki stops being navigable past about fifty entries, and "which
approaches have failed for this kind of treatment" is a query, not a read.

No embeddings: they would need an API key, and DuckDB's FTS plus grep is ample
at this scale.

## At three hundred questions

A question a day across a few analysts is a few hundred records inside a year,
and that is the size this is built for rather than a size it survives.

It works because the two halves grow differently. Questions grow with the
asking: one directory each, forever, and nobody browses them. The wiki does
not — the tenth churn question adds a record but still only one `churn_90d.md`,
so the thing people actually read stays roughly the size it is now. Everything
learned is deduplicated into the concept, and the question record keeps only
what was found.

Which makes the archive a retrieval problem, and retrieval is the index's job,
not the directory tree's:

```bash
cb status                     # what is open, freshest first; --all for the archive
cb methods                    # what this company has estimated with before
cb find "add-on churn"        # ranked, and the terms need not sit next to each other
cb context <qid>              # priors ranked by shared variables, tail counted
```

`cb ask` says so when the question has been asked before. `cb gaps` ages a
stalled question out after a fortnight, because with several analysts at work
"not yet concluded" is the normal state and a gap that fires on all of them is
one nobody reads.

The last piece is the way back. `cb index` writes a `## Questions asked here`
block onto each node file — generated, inside `<!-- cb:managed -->` markers, so
the prose around it is untouched. Browsing `churn_90d.md` in Obsidian then shows
the variable, why it reads as a false zero under 90 days, and every question
that ever turned on it. That is the difference between an archive and a wiki:
you navigate from the concept, and never have to open `questions/` at all.

## Validation

```bash
cb doctor
```

Catches what silently corrupts verdicts: cycles, dangling links, contradictory
edge metadata, and an arithmetic edge mistyped as causal. Warns about
unconfirmed edges and unobserved nodes without a source.

## Rules that do not bend

- Refuse when identification is not possible, and always say what design would work.
- Never dead-end. Try the unfamiliar thing or hand over a notebook; never argue
  the question was ill-posed instead of answering it.
- Claude does not quietly change causal structure. Adding an edge during an
  interview is fine — the analyst is right there. Changing a confirmed edge means
  asking. Every edge records who confirmed it and when.
- Everything ends recorded, including abandoned questions and failed notebooks.
  Those are the useful ones — `abandoned` without a reason fails validation.
- A notebook run outside and brought back is completed work, not an error.
- No required `--treatment` / `--outcome`. What the treatment is, or whether
  there is one, comes out of the interview.

## The worked example

[examples/toy-company/](examples/toy-company/) is a complete project: a travel
company with two named graphs, an eligibility rule that _is_ the confounding, an
unobserved variable that forces a refusal, and three questions — one identified
by backdoor adjustment, one refused, one re-posed because the outcome was an
accounting identity.

```bash
cd examples/toy-company
cb doctor && cb identify q-0001 && cb identify q-0002
```

## Tests

```bash
pytest
```

109 tests. The identification ones are golden tests against textbook DAGs with
known answers — backdoor, frontdoor, IV, bow arc, M-bias — so that a DoWhy
upgrade that changes semantics breaks the suite instead of quietly certifying an
unanswerable question.

Two tests guard the templates: one asserts the markdown is readable as package
data (so a wheel cannot ship the code without the skills), and one asserts this
repo's own `skills/` and `.claude/commands/cb/` still match `cb/templates/`. If
you edit a skill in place, that second test tells you to edit the template
instead and run `cb sync --force` — otherwise every new project would get the
stale version.

# Tl DR

cb init gives you wiki/, questions/, raw/, skills/, CLAUDE.md and .claude/commands/cb/. From there:

Drop things into raw/ — a semantic layer export, notes on how a process works, an old analysis writeup. Anything.
claude, then /cb:ingest — schema exports get imported automatically; everything else I read and write into the wiki.
Repeat 1–2 as you pick things up. No question needed yet; this is just building context.
When a question arrives: /cb:ask "whatever they said" — and the interview starts from what the wiki already knows.
The one thing that makes this pay off is step 3: the eligibility rules, the columns that are measured after treatment, the joins that don't work. That's the material that makes the tenth question cheap.
