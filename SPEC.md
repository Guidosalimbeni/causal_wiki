# cb — specification

_A description of this repository complete enough to rebuild it from. Written for
a reader (human or model) who has never seen the code._

---

## 1. What it is, in one paragraph

`cb` is a companion for doing **causal analysis inside a single company**. It is a
Python CLI plus a markdown wiki plus a set of prose instructions for an LLM. The
wiki accumulates what has been learned about that company's data, its business
rules, its causal graph, and which analysis designs actually worked there — so
the tenth causal question is cheaper to answer than the first. The CLI never
calls an LLM and holds no API key: it is driven from Claude Code, where the
judgement happens. Everything a human or a model writes is markdown in git; the
only database is a derived DuckDB file that is dropped and rebuilt on demand.

Stack: Python ≥3.11, `networkx`, `dowhy` ≥0.14, `duckdb`, `pyyaml`, `nbformat`,
`typer`, `pydantic` v2. Entry point `cb = cb.cli:app`. ~4,100 lines of package
code, ~1,600 lines of tests (174 passing).

---

## 2. The central idea

Causal analysis inside a company fails for reasons that are almost never
statistical:

- The **assignment mechanism** — the business rule that decides who gets treated
  — is the confounding, and it is written down nowhere.
- Whether a column is recorded **before or after** the treatment decides whether
  adjusting on it is a control or a catastrophe. No semantic layer records this.
- The same question gets asked again a year later, and nobody remembers that it
  was refused, or why.
- An LLM asked "is this identified?" is *usually* right, and fails exactly when
  there is a deadline and someone wants a number.

So the tool splits along a single seam:

| half | owns | form |
| --- | --- | --- |
| **`cb`** (deterministic Python) | identification, the markdown parser, the records and their schemas, the notebook scaffolds, validation, the index | code, tested, no LLM |
| **the judgement layer** | the interview, routing raw material, critiquing a question, proposing edges, choosing an estimator, writing up | prose in `skills/*.md`, read by the model |

The seam is the design. Anything that must be the same every time is code.
Anything that is genuinely judgement is prose the user can edit. `cb ask` opens
a record and assembles context — it does not conduct the interview, because that
can only happen in a conversation.

Three failure modes are engineered against explicitly, and each one shaped an
enforced invariant:

1. **A confident wrong number.** → identification is code, and a verdict cannot
   be talked past.
2. **A dead end.** → a refusal that does not name a design that would work
   cannot even be serialized (pydantic validator).
3. **The model teaching itself its own guesses.** → every causal edge records
   who confirmed it and when; unconfirmed edges make any verdict resting on them
   `provisional`.

---

## 3. Layout

```
cb/
  cli.py             the whole command surface (typer)
  config.py          where things live; project root discovery
  ingest.py          raw/ -> table docs, deterministic half only
  doctor.py          validation
  context.py         ranking prior questions for one new question
  templates.py       writing the judgement layer into a user's project
  identify/
    engine.py        the identification algorithm and the two DoWhy guards
    report.py        the verdict schema (refusal must carry a design)
    expand.py        arithmetic/definitional expansion
  wiki/
    frontmatter.py   markdown + YAML frontmatter, canonical round-trip
    nodes.py         parse one node file into a Node and typed Edges
    graph.py         nodes -> two networkx DiGraphs (causal, arithmetic)
    managed.py       generated regions inside human-owned files
    methods.py       the wiki/methods/ folder and which questions used each note
    backlinks.py     write "Questions asked here" back onto node files
  records/
    question.py      the question record + status state machine
    interview.py     interview.yaml schema (deliberately permissive)
    result.py        bringing an executed notebook back
  index/
    build.py         drop and rebuild the DuckDB index from markdown
    queries.py       gaps, full-text find, arbitrary SQL
  notebook/
    scaffold.py      analysis notebook and experiment-design notebook
  templates/         the judgement layer, shipped as package data
    skills/*.md      routing, interview, critique, edges, methods, writeup
    commands/*.md    /cb:ingest /cb:ask /cb:resume /cb:gaps
    project/CLAUDE.md  the standing context written into a user's project

skills/                 materialised copies of cb/templates/skills/
.claude/commands/cb/    materialised copies of cb/templates/commands/
examples/toy-company/   a complete worked project
tests/
```

**The two-copy rule.** `skills/` and `.claude/commands/cb/` at the repo root are
*materialised copies* of `cb/templates/`. Edit the template, then run
`cb sync --force`. `tests/test_templates.py` fails on drift, and separately
asserts the templates are readable as package data (so a wheel cannot ship the
code without the judgement layer).

---

## 4. A project on disk

`cb init .` creates this in a user's repo. A cb project is *any* directory
containing a `wiki/` folder; the root is found by walking up from the cwd, as
git does.

```
wiki/
  data/tables/   one file per table: columns, joins, filters, causal annotations
  graph/         one file per variable — the causal graph
  rules/         business rules; these decide who gets treated
  process/       how the business actually works, in prose
  methods/       how this company estimates and tests things — the tailoring
  experiments/   what was run and what it found
  traps/         mistakes that keep getting made here
questions/q-NNNN-slug/
  question.md          frontmatter + the question as asked
  interview.yaml       stage three
  identification.json  + a rendered identification.md
  notebooks/           scaffolded notebooks
  results/             executed notebooks brought back
  log.md               append-only stage stamps
raw/             dropped-in source material, not yet read into the wiki
skills/          the judgement layer (editable)
CLAUDE.md        always-on context for Claude Code
.claude/commands/cb/
.cb/             derived: index.duckdb, ingest.json manifest — gitignored
```

Everything a human reads is markdown, readable in Obsidian. The DuckDB index is
derived, disposable, and never authoritative, which is why it can never drift
from the source.

### 4.1 Node files — the causal graph

One markdown file per variable. Obsidian's graph view has no direction and no
edge types, so **the headings carry them**:

```markdown
---
id: addon_shown
label: Flexible-dates add-on shown at checkout
observed: true              # absent means observed; being unobserved is the claim
table: fact_booking.addon_impression_flag
measured: at_quote          # before or after the treatment — the critical field
causal_role: treatment      # treatment|outcome|confounder|mediator|collider|proxy|instrument|unspecified
graphs: [addon_uptake]      # the ONLY source of graph membership; no manifest
source: raw/2026-08-semantic-layer.csv
confirmed_by: guido
confirmed_at: 2026-08-29
---

Prose about what this variable really is.

## Caused by
- [[lead_time_days]] — rule threshold at 60 days <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 -->

## Causes
- [[addon_purchased]] — you cannot buy what you were never shown <!-- cb: confirmed_by=guido -->

## Computed from
(arithmetic only — never enters the causal graph)
```

Parsing rules (`cb/wiki/nodes.py`):

- `## Caused by` → incoming causal edge; `## Causes` → outgoing causal;
  `## Computed from` → **arithmetic** edge. Headings are matched
  case-insensitively with trailing colons stripped.
- A list item is an edge only if it contains a wikilink; a bullet of prose is
  ignored. Wikilinks may carry `folder/`, `#heading` and `|alias` — the node id
  is the basename.
- Machine fields live in an HTML comment `<!-- cb: key=value ... -->` so
  Obsidian's reading view stays clean while staying greppable. The text left
  after removing the link and the comment is the edge's **reason**.
- An edge may be declared on either endpoint or both; `graph.reconcile()`
  **unions** them. Only contradictory `confirmed_by`/`confirmed_at` is an error.
- `confirmed_by` defaults to the sentinel `claude-proposed`, which means
  *unconfirmed*.
- Files (or directories) whose name starts with `_` are prose, not nodes.
  Duplicate node ids are an error.

`Wiki.causal()` and `Wiki.arithmetic()` produce two separate `networkx.DiGraph`s.
Keeping them apart is the entire point: `net_revenue = revenue × (1 - churn)` is
exactly true and says nothing about cause, so it must never be certifiable as a
causal finding. `cb doctor` errors if the same edge is declared both ways.

### 4.2 Managed regions — re-import safety

Generated content lives between markers inside human-owned files:

```
<!-- cb:managed name=schema source=raw/semantic-layer.csv sha=ab12cd -->
...generated...
<!-- /cb:managed -->
```

Ingest and `cb index` may only ever rewrite the bytes between the markers.
Everything outside is human territory — and the causal annotations written on
top of an import are the most valuable thing in the wiki, recorded nowhere else.
A region that has nothing to say is removed rather than left empty.

### 4.3 The question record

`question.md` frontmatter is a pydantic model with two enforced invariants.

```yaml
id: q-0001
status: draft|interviewing|identified|refused|notebook|analysing|concluded|abandoned
question: "Does showing the flexible-dates add-on actually reduce cancellations?"
asked_by: guido
asked_on: '2026-08-29'
graph: addon_uptake
treatment: [addon_shown]
outcome: [churn_90d]
verdict: IDENTIFIED
method: backdoor.propensity_score_weighting
treatment_kind: ui_impression
effect: "-2.1pp (95% CI -3.5 to -0.8)"
finding: "Showing the add-on reduces 90-day cancellation by about 2 points."
design: "10% account-level holdout, rep calls suppressed for six weeks"
design_status: proposed|agreed|running|ran|declined
experiment: 2026-q1-rep-call-holdout    # required once design_status is `ran`
abandoned_reason: "..."                 # required when status is `abandoned`
```

- `design_status` with no `design` is refused by the schema — "say what would be
  run, not just that something would be".
- `design_status: ran` without `experiment` is refused.
- `status: abandoned` without `abandoned_reason` is refused, because the
  abandoned questions and the failed notebooks are the ones worth learning from.

Ids are `q-NNNN`, allocated as max-on-disk + 1; the directory is
`q-NNNN-<slug>` where the slug is the first five content words. `log.md` is
appended to at every stage (`- \`<iso timestamp>\` **stage** — note`), and
**last activity is read from the log**, not from file mtime, which a fresh clone
resets — this is what lets `cb gaps` age a stalled question out after 14 days.

### 4.4 interview.yaml

Deliberately permissive (`extra="allow"` throughout): the interview is judgement,
and a rigid schema would turn it into a fixed menu of question types. It carries
`posed_as`, `treatment`, `outcome`, `population`, `period`, a list of `turns`
(`asked` / `answered` / `established`), proposed `edges`, `assumptions`,
`open_questions`, `wiki_gaps`, and `ready: bool`. `ready: false` with a list of
what is missing is a perfectly good outcome. `searchable_text()` flattens it for
the full-text index — future questions search past interviews, which is the whole
reason to write one.

---

## 5. The five stages

```
/cb:ingest                     1. collecting — raw/ into the wiki
/cb:ask "<what they asked>"    2. a question arrives; a record is opened
                               3. the interview — the heart of it
                               4. a notebook, run where the data is
cb result add <qid> <nb>       5. it comes back; refine, re-run, or conclude
```

Every question gets an id and all five stages hang off `questions/q-NNNN-slug/`.
Stage 3.5 — identification — is the one step that is code.

---

## 6. Identification (`cb identify <qid>`)

The algorithm, in order:

1. **Resolve the graph.** Load `wiki/graph/`. Error if any treatment/outcome
   node has no file. If a named graph is given, subgraph to its members. Error
   on a cycle — identification is undefined there.
2. **Definitional expansion, first.** If a treatment or outcome is defined by
   arithmetic edges, resolve it depth-first to the leaves of its definition and
   return `NEEDS_EXPANSION` with those components. Excluding arithmetic edges
   from the causal graph is right; silently *dropping* the node is not, because
   that edge may be the only thing connecting the outcome to anything, and the
   question would then be refused for the wrong reason.
3. **Restrict the graph** to what can matter: ancestors of treatment and outcome,
   plus every simple path from treatment to outcome (which carries the
   mediators). A smaller graph makes the verdict readable.
4. **Ask DoWhy** — `identify_effect_auto(g, T, Y, observed, NONPARAMETRIC_ATE)`.
5. **Guard one.** `identify_effect_auto` does **not raise** on an unidentifiable
   effect. It returns all-`None` estimands, or — when no directed path exists —
   an `estimands` attribute that is itself `None`. Both shapes are handled
   explicitly, and `no_directed_path` returns `NO_DIRECTED_PATH`.
6. **Guard two.** DoWhy will hand back an estimand that requires a variable
   declared unobserved. On an M-bias graph with observed `{Z,T,Y}` it proposes
   the latent `U1` as an instrument, with a full estimand expression. Trusting
   `estimands['iv'] is not None` would certify a design requiring a variable we
   have said is unmeasurable — the exact failure this tool exists to prevent. So
   **every strategy's variables are filtered against the observed set**; leaked
   ones are discarded and reported under "Discarded".
7. **Verdict.** Surviving strategies (`backdoor`, `frontdoor`, `iv`,
   `general_adjustment`) → `IDENTIFIED`. None → `NO_CRITERION_FOUND`, naming the
   unobserved common causes (unobserved ancestors of both treatment and outcome)
   as the blocking nodes.
8. **Provisionality.** Unconfirmed causal edges *inside the restricted subgraph*
   are listed and the report is stamped `provisional`. This replaces an approval
   queue: pressure to confirm an edge arrives when it is load-bearing for a real
   verdict, not as a backlog.

Four verdicts:

| verdict | meaning |
| --- | --- |
| `IDENTIFIED` | a criterion over observed variables yields the effect |
| `NO_CRITERION_FOUND` | no backdoor/frontdoor/IV strategy over the observed nodes |
| `NO_DIRECTED_PATH` | as drawn, the treatment cannot affect the outcome |
| `NEEDS_EXPANSION` | an endpoint is an accounting identity; re-pose it |

`NO_CRITERION_FOUND` is deliberately **not** called "unidentifiable": DoWhy's
search is sound, and completeness is not claimed. (Its ID-algorithm
implementation takes no `observed_nodes` argument and treats every node as
measured, so it cannot supply that proof.)

**A refusal cannot be serialized without `design_alternative`** — a pydantic
`model_validator` on `Report` enforces it. The generated text names, in rough
order of cost: measure the latent (or find a proxy), randomise, find an
instrument, find a full mediator, and — always — use a design whose assumptions
a DAG cannot express (DiD, synthetic control, RDD, interrupted time series),
with an explicit statement that this verdict is *not* evidence against them.

Side effects: `identification.json` + a rendered `identification.md` are written
into the question directory, `verdict` and `status` are set on the record, and
the process exits **2** on a refusal (so a script cannot ignore it).

One more repair worth knowing about: dowhy 0.14 renders a single outcome
`churn_90d` as `c,h,u,r,n,_,9,0,d` in its assumption strings because it joins the
string rather than the list containing it. The text is shown next to the verdict,
so it is mended before display.

---

## 7. The judgement layer

Prose, shipped as package data, written into a project by `cb init` and
refreshed by `cb sync`. **Nothing ever overwrites a file the user has edited** —
skills are meant to be changed; a differing file is reported as `kept`, and only
`--force` replaces it. `sync` never touches `CLAUDE.md` (a project's own
standing context), except to restore it if it is *missing*, which is not an edit.

- `CLAUDE.md` — always-on context: I am a causal analyst here, not a reporting
  one; the graph decides what is adjustable and `cb identify` decides what is
  identified, not my reading of either; where everything lives; the rules that
  do not bend.
- `skills/routing.md` — where each kind of raw material goes. **Ingest never
  writes a causal edge**; a causal claim in a document is recorded as an
  attributed claim in prose. Business rules get special attention: a rule that
  decides who gets treated *is* the assignment mechanism and therefore *is* the
  confounding.
- `skills/interview.md` — the heart. Ask one thing at a time; ask what only they
  know ("how does someone end up in this group?" — that answer is the assignment
  mechanism); chase the timing of every variable; ask early whether an experiment
  is even possible, because a refusal whose only proposal is "randomise it" is a
  dead end when randomisation was never on the table. Write nodes and edges into
  the wiki *during* the interview.
- `skills/critique.md` — is it descriptive, predictive or causal? Is the
  treatment something anyone can intervene on? Watch the shown-versus-chosen
  split (the business controls the offer, not the uptake). Is the outcome a real
  quantity, or an identity, or only observed for survivors? Is the population and
  window stated?
- `skills/edges.md` — new edge with the analyst present → write it confirmed;
  nobody has agreed → `claude-proposed`; contradicts a confirmed edge → **stop
  and ask**; deleting → always ask. The reasoning line is not decoration: it is
  what a future session uses to decide whether the edge still holds.
- `skills/methods.md` — identification is a closed list; estimation is not. Read
  `wiki/methods/` first. Randomisation is not the fallback. Sensitivity analysis
  by default. If the analyst asks for something specific, **try it** — disagreeing
  while delivering is fine, refusing to deliver because you disagree is not.
- `skills/writeup.md` — two different things get written: *what was found* on the
  question record, *what was learned* into the wiki. "If the answer came out and
  the wiki is unchanged, look again."

Slash commands `/cb:ingest`, `/cb:ask`, `/cb:resume`, `/cb:gaps` are the actual
entry points; each is a short procedure that calls `cb` and points at a skill.

---

## 8. Ingest

`cb ingest` walks `raw/`, hashes each file against `.cb/ingest.json`, and marks
it `new` / `changed` / `seen`. A file that parses as a schema export (CSV, YAML
or JSON, in either flat-rows or nested `{tables: {name: {columns: ...}}}` shape,
with fuzzy key matching for table/column/type/description) is imported into
`wiki/data/tables/<table>.md`:

- the rendered column table goes into the `name=schema` managed region;
- the `columns:` frontmatter list is **merged**, keeping every human annotation;
- a column that has vanished upstream is marked `status: retired`, **never
  deleted** — the reason someone marked it a collider outlives the column;
- a retired column that reappears is un-retired.

Everything else is listed as needing judgement, and routed by the model
following `skills/routing.md`.

**Ingest writes no causal edges at all.** This is the fix for an approval queue
that once produced 29 pending items nobody read, so nothing got built. Facts land
in ingest; the graph is drawn in the interview, where the analyst is already
answering questions and approval is part of the conversation.

---

## 9. The index

```bash
cb index   # drop and rebuild .cb/index.duckdb from the wiki
cb gaps    # what haven't we looked at?
cb find "add-on churn"
cb sql "SELECT method, verdict, count(*) FROM effects GROUP BY 1,2"
```

Tables: `nodes`, `edges`, `questions`, `effects`, `experiments`, `columns_`,
`docs`. `docs` is the full-text corpus (interviews, questions, tables, methods,
experiments, traps, rules, process) indexed with DuckDB's FTS extension; `cb find`
falls back to a per-term LIKE score when the extension cannot load. No
embeddings — they would need an API key, and FTS plus grep is ample below a few
thousand documents.

Two subtleties worth reproducing: every `docs` row needs a **unique** id or
`match_bm25` silently returns nothing (a question and its interview share a
`ref`); and generated/boilerplate text is stripped before indexing, or every
unannotated table matches every query about mediators and colliders.

`cb index` also writes a generated `## Questions asked here` block back onto each
node file, and `## Questions that reached for this` onto each method note — inside
managed markers. That is the way back: browsing `churn_90d.md` in Obsidian shows
the variable, why it reads as a false zero under 90 days, and every question that
ever turned on it. You navigate from the concept and never have to open
`questions/` at all.

`cb gaps` is a list of SQL queries with a human explanation each: unconfirmed
edge, isolated node, unobserved node, unannotated table, **column without
timing**, stalled question (>14 days), question without interview, **refusal
without a design**, **design waiting** (proposed/agreed/running and never came
back), method used with no note written up, abandoned without a reason.

---

## 10. Notebooks

`cb notebook new <qid>` writes an analysis skeleton carrying the identification
verdict in its header — the analyst cannot run it without seeing what was
assumed. Parameters (`TREATMENT`, `OUTCOME`, `ADJUSTMENT_SET`, `STRATEGY`) come
from the report, "from identification, not from judgement". Sanity checks come
*before* estimation. The verb matters: backdoor → "adjust for", frontdoor →
"estimate in two stages through", IV → "instrument with"; saying "adjust for" a
frontdoor mediator would invite the precise mistake the wiki records as a trap.
A notebook scaffolded for a refused question says so and forbids a causal
estimate.

`cb notebook new <qid> --design` writes an **experiment design** notebook:
power and the sample size the MDE actually costs, deterministic hash assignment,
the SRM and balance checks that catch a broken test, and a pre-registered
analysis plan (intention-to-treat, covariates named in advance, one primary
metric, a stopping rule). It works **whatever the verdict was**, in three
situations: as *the answer* when nothing observational recovers the effect; on
*request*, because "give me a design instead" is a causal question in its own
right and is never met with a refusal; and as *confirmation* when an estimate did
come out, since two designs with different assumptions agreeing is worth more
than either alone.

`cb result add <qid> <path>` copies an executed `.ipynb` into `results/` **and**
renders it to readable markdown, keeping error tracebacks deliberately — a
notebook run outside and brought back is completed work, not an error, and the
runs that failed are the ones worth keeping.

---

## 11. Validation (`cb doctor`)

Errors (exit 1): a dangling wikilink; contradictory edge metadata; an edge
declared both causal and arithmetic; a cycle in either graph; a malformed
question record; **two questions with the same id** (ids are max+1 on disk, so
two analysts on two branches collide at the merge, by which time the id is in
file paths); `abandoned` with no reason; an `experiment:` pointing at a note that
does not exist; a malformed `columns:` list.

Warnings: no `CLAUDE.md` (the standing context is markdown, so its absence is
silent — the project would still answer, just not as causal work); a node in no
named graph; an unobserved node with no `source` (a refusal will name it, so it
should say where the claim came from); an unconfirmed edge; a question concluded
on a non-`IDENTIFIED` verdict.

---

## 12. Scale

The design target is a few hundred questions — a question a day across a few
analysts for a year — and it works because the two halves grow differently.
Questions grow with the asking: one directory each, forever, and nobody browses
them. The wiki does not: the tenth churn question adds a record but still only
one `churn_90d.md`. Everything learned is deduplicated into the concept; the
question record keeps only what was found.

That makes the archive a retrieval problem, handled by the index rather than the
directory tree: `cb status` (open questions, freshest first; closed ones counted,
not listed), `cb context <qid>` (priors **ranked** — shared variables 5, graph
neighbours 2, same named graph 2, wording match 2 — with the tail counted and the
command to see it printed), `cb find`, `cb methods`. `cb ask` warns when a new
question shares at least half its content words (Jaccard) with one already on record, computed
without the index, because `cb ask` runs before anyone rebuilds it and a stale
index is exactly when a duplicate slips through.

---

## 13. Rules that do not bend

1. **Refuse when identification is not possible, and always say what design would
   work.** Enforced: `Report` will not validate without `design_alternative`.
2. **Never dead-end.** Try the unfamiliar thing or hand over a notebook; never
   argue the question was ill-posed instead of answering it.
3. **Never quietly change causal structure.** Adding an edge during an interview
   is fine — the analyst is right there. Changing a *confirmed* edge means
   asking. Every edge records who confirmed it and when.
4. **Everything ends recorded**, including abandoned questions and failed
   notebooks. Those are the useful ones. `abandoned` without a reason fails
   validation.
5. **A notebook run outside and brought back is completed work**, not a fallback.
6. **No required `--treatment` / `--outcome`.** What the treatment is, or whether
   there is one, comes out of the interview.
7. **Arithmetic is not cause.** `## Computed from` never enters the causal graph.
8. **Ingest writes no causal edges.**

---

## 14. Deliberate non-choices

| rejected | why |
| --- | --- |
| LLM-judged identification | usually right, and fails under deadline pressure — the exact case this exists for |
| an approval queue for proposed edges | tried; one document produced 29 pending items nobody read. Replaced by confirm-in-the-interview plus `provisional` verdicts |
| embeddings / a vector store | would need an API key; DuckDB FTS plus grep is ample at this scale |
| a database as source of truth | markdown in git is the only thing anyone writes, so the index can be dropped and rebuilt and can never drift |
| a graph manifest file | node frontmatter `graphs:` is the only source of membership, so nothing can fall out of sync |
| deleting columns that vanish upstream | retired instead — the annotation outlives the column |
| calling a refusal "unidentifiable" | DoWhy's search is sound but not proven complete here; say what is known and no more |

---

## 15. Rebuilding it

A sensible build order, each step testable on its own:

1. `wiki/frontmatter.py` — canonical round-trip of `---\nyaml\n---\n\nbody`, with
   a fixed key order so git diffs stay readable.
2. `wiki/nodes.py` + `wiki/graph.py` — the parser and the two DiGraphs, including
   edge reconciliation and conflict detection.
3. `config.py`, `records/question.py` — project discovery and the record schema
   with its validators.
4. `identify/` — `expand.py`, then `engine.py` with both DoWhy guards, then
   `report.py` with the refusal validator. **Write the golden tests first**:
   textbook DAGs with known answers — backdoor, frontdoor, IV, bow arc, M-bias —
   so a DoWhy upgrade that changes semantics breaks the suite instead of quietly
   certifying an unanswerable question.
5. `wiki/managed.py`, then `ingest.py` on top of it.
6. `index/` and `doctor.py`.
7. `notebook/scaffold.py`, `records/result.py`.
8. `templates.py` and the prose layer; plus the two template tests (package data
   readable; repo copies match).
9. `cli.py` wiring it together, and `examples/toy-company/` as an end-to-end
   fixture: two named graphs, an eligibility rule that *is* the confounding, an
   unobserved variable that forces a refusal, and three questions — one identified
   by backdoor adjustment, one refused, one re-posed because the outcome was an
   accounting identity. `cd examples/toy-company && cb doctor && cb identify q-0001`.

The prose layer is not optional garnish. `cb` alone will answer every command and
still let someone produce a confident wrong number; the skills and `CLAUDE.md` are
what make it causal work rather than a query tool. That is why `cb doctor` warns
when `CLAUDE.md` is missing, and why `cb sync` writes it back.
