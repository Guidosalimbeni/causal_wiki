# Skills

Judgement lives here, not in `cb`. Causal inference is a huge field and Claude
knows more of it than could sensibly be encoded, so these are prose instructions
rather than a fixed menu of methods or question types.

Where a skill names methods it is illustrating a distinction, never bounding the
options. The only closed list in this tool is what `cb identify` returns, and
that is DoWhy's vocabulary for *identification* — not a statement about which
estimators exist, and not a view on designs whose assumptions a DAG cannot
express. Act as the expert; the notes in `wiki/methods/` are what this company
has learned on top of that, and they are the part worth reading twice.

`cb` owns only what must be deterministic: identification, the parser, the
records, the notebook scaffold, validation, and the index.

| skill | when |
| --- | --- |
| [routing.md](routing.md) | `cb ingest` listed a document that needs judgement |
| [interview.md](interview.md) | stage three, after `cb ask` — the heart of the tool |
| [critique.md](critique.md) | before identification, to check the question is well posed |
| [edges.md](edges.md) | proposing a causal edge during an interview |
| [methods.md](methods.md) | identification passed, choosing how to estimate |
| [writeup.md](writeup.md) | stage five, recording what was found and learned |

## Rules that do not bend

1. **Refuse when identification is not possible, and always say what design would
   work.** `cb identify` enforces the second half — a refusal will not serialize
   without a `design_alternative`.
2. **Never dead-end.** If the analyst asks for `dowhy.gcm` or something you have
   not seen, try it or hand over a notebook. Never argue the question was
   ill-posed. This is the worst failure available and it has happened before.
3. **Do not quietly change causal structure.** Adding an edge during an
   interview is fine — the analyst is right there. Changing an edge already
   confirmed means asking. Every edge records who confirmed it and when.
   Otherwise Claude writes a graph, reads it back next session as fact, and
   teaches itself its own guesses.
4. **Everything ends recorded**, including abandoned questions and failed
   notebooks. Those are the useful ones.
5. **A notebook run outside and brought back is completed work, not an error.**
   It is the normal path.
6. **Never require a treatment or outcome up front.** What the treatment is, or
   whether there is one, comes out of the interview.
