Plan a small Python library called `cb`. Don't write code yet. Produce a plan, and push
back on anything below you think is wrong.

WHAT IT IS
A companion for causal analysis inside a company. It remembers what's been learned about
that company's data and about which designs actually worked there, so the tenth question
is cheaper to answer than the first. I run it through Claude Code on a subscription, so
no API key. Python, DuckDB, git, markdown.

HOW IT GETS USED

Stage one: collecting. I'm a data scientist. Over time I pick things up — where a table
lives, what its columns mean, a semantic layer export, the joins that actually work, the
filters you always need, how a business process runs, what an old experiment found. I
drop all of it into raw/ and run `cb ingest`. It gets read, organised and written into
the wiki, with a link back to the file it came from. No question is in my head yet. This
is just building up context.

Stage two: a question arrives. Someone in the business wants to know something. I run
`cb ask "<whatever they said>"`. It can be any kind of causal question: does X cause Y,
what's driving a change in Y, how should we design an A/B test for this, is this even
answerable. The whole field, not a fixed menu.

Stage three: the interview. This is the heart of it. Claude reads the wiki and asks me
questions — informed ones, because it already knows the tables, the process and what's
been tried. It's working towards three things: what the causal graph looks like, how the
question should actually be posed, and whether it now understands the situation well
enough to proceed. The interview gets saved as YAML. It is not a transcript to be filed
away — future questions search it, so a good interview makes the next one shorter.

Stage four: the notebook. Claude writes a notebook, saves it in notebooks/, and links it
to the question. I take it away and run it in my own environment, because that's where
the data is.

Stage five: I come back with the output. Claude reads it and we keep going — refine,
re-run, or conclude. When we're done, what was found and what was learned is written
back into the wiki.

Every question gets an id, and all five stages hang off it.

THE WIKI
Markdown in git. I read and edit it, and I read it in Obsidian. Design the layout
yourself, don't give me twelve folders. But these aren't the same kind of thing:

- Data — where things live, tables, columns, what they mean, joins that work, filters
  you always need. Often imported from a semantic layer, so it gets re-imported.
  Re-importing must never wipe out what's been added on top.
- Causal annotations on columns — is this measured before or after the treatment? Is it
  a mediator, a collider, a proxy? No semantic layer records this, and it's the most
  common source of wrong analysis. This is the most valuable thing in the wiki.
- Metrics and the arithmetic between them — net_revenue = revenue x (1 - churn). These
  are exactly true and tell you nothing about cause. They must be a different kind of
  edge from causal ones, or the identification step will happily certify an accounting
  identity as a finding.
- Business rules and policies — "the add-on only shows when lead time is over 60 days
  and value is over 800". These matter more than they look: a rule like this IS the
  mechanism that decides who gets treated, so it IS the confounding. Usually written
  down nowhere else.
- Process — how the business actually works, in prose.
- Past experiments and what they found.
- Traps — mistakes that keep getting made in this domain.

Everything says where it came from. The wiki has to be easy for Claude to navigate:
consistent frontmatter, a generated index, predictable names. Claude finds things by
reading and grepping, so organise it for reading.

THE CAUSAL GRAPH LIVES IN THE WIKI, ONE MARKDOWN FILE PER NODE
I want to see and check the graph in Obsidian. Obsidian's graph view has no direction
and no edge types, so links alone aren't enough. Suggested scheme — improve it if you
can. Frontmatter holds the machine fields: observed true/false, causal role, when it's
measured, source, who confirmed it. Typed sections hold the edges, and the heading gives
the direction and kind: "## Caused by", "## Causes", "## Computed from" for arithmetic.
Each entry is a link plus one line of reasoning. A parser turns these files into a
NetworkX graph. Several named graphs need to coexist so I don't end up with one
unreadable blob.

This means Claude can check whether a graph already exists for an area, extend it, or
tell me what's missing, just by reading the wiki.

WHAT I THINK NEEDS TO BE CODE — challenge this, I may be wrong

Only one thing genuinely does: identification. Given the graph and the question, work out
whether the effect can be identified from what's observed. Graph algorithms, no LLM.
Global d-separation over the observed nodes decides it. If a node marked observed:false
sits on a path that can't be blocked, the answer is a refusal, not a caveat — and it must
name the node and say what design would work instead. Arithmetic edges are excluded
entirely. One warning from experience: DoWhy's identify_effect does NOT raise an error
when an effect is unidentifiable. It returns an object whose estimands are all None. If
you don't check that explicitly, every unanswerable question gets certified.

This is code and not judgement for one reason: an LLM asked "is this identified?" usually
gets it right, and "usually" fails exactly when there's a deadline and someone wants a
number. That's the case the whole thing exists for.

Three smaller pieces of plumbing: a parser from the node files to a graph, writes to the
question record, and generating the notebook. Tell me if you think more is needed, and
say why.

Everything else is a skill — markdown under skills/. The interview, the critique of a
question, how to route ingested material, how to propose graph edges, suggesting methods,
writing up what was learned. Deliberately not code, because I don't want a fixed menu of
methods or question types. Causal inference is huge and Claude knows more of it than I'll
ever encode.

WHERE THE DATABASE EARNS ITS PLACE
DuckDB, for things I'd count, filter or join rather than read: one row per question with
its outcome, effects that have been estimated, past experiments. The wiki becomes
unnavigable past about fifty entries, and "which approaches have failed for this kind of
treatment" is a query, not a read. Keep it small. If I'd only ever read it, it belongs in
the wiki.

RULES THAT SHOULDN'T BEND

- Refuse when identification isn't possible, and always say what design would work.
- Never dead-end. If I say "try dowhy.gcm" or ask something unfamiliar, try it or hand
  me a notebook — never argue the question was ill-posed. That failure mode is the worst
  one available and it's happened before.
- Claude doesn't quietly change causal structure. Adding an edge during an interview is
  fine, I'm right there. Changing an edge I already confirmed means asking me. Every
  edge records who confirmed it and when. Otherwise Claude writes a graph, reads it back
  next session as fact, and teaches itself its own guesses.
- Everything ends recorded, including the questions we abandon and the notebooks that
  failed. Those are the useful ones, and a system that only logs successes never learns
  from them.
- A notebook run outside Claude Code and brought back is a completed piece of work, not
  an error. It's the normal path, not the fallback.
- No required --treatment/--outcome arguments. What the treatment is, or whether there
  is one, comes out of the interview.

WHAT I THINK I CAN CUT — tell me if I'm wrong
An approval queue for graph changes. I had one, and ingesting a single document produced
29 pending items that I never reviewed, so nothing ever got built. I think the fix is
that ingest stores facts and doesn't invent causal claims, and the graph gets drawn in
the interview where I'm already answering questions. Approval becomes part of the
conversation instead of a queue.

SURFACE
`cb ingest` and `cb ask`. Maybe `cb gaps` for "what haven't we looked at?".
