# Proposing graph edges

## The rule that protects the graph from you

Adding an edge during an interview is fine — the analyst is right there and can
say no. **Changing an edge already confirmed means asking first.**

Every edge records who confirmed it and when. Without that, Claude writes a
graph, reads it back next session as fact, and teaches itself its own guesses.
That failure is silent and compounds.

- New edge, analyst present, they agree → write it with `confirmed_by=<them>`.
- New edge, nobody has agreed yet → write it with `confirmed_by=claude-proposed`.
- Contradicts a confirmed edge → **stop and ask.** Do not edit it.
- Deleting an edge → always ask.

An edge marked `claude-proposed` is not blocked, it is just visible: any verdict
resting on it comes back stamped `provisional` and lists it, and `cb gaps`
surfaces it. That is the whole approval mechanism, and it applies pressure only
where it is load-bearing.

## The three kinds of edge

```markdown
## Caused by       incoming causal    parent -> this node
## Causes          outgoing causal    this node -> child
## Computed from   arithmetic         a definition, never causal
```

`## Computed from` is not a weaker causal edge. `net_revenue = revenue x (1 -
churn)` is exactly true and tells you nothing about cause. Kept separate, it
cannot be certified as a finding; mixed in, it would be. `cb doctor` fails if an
edge is declared both ways.

## Writing one

```markdown
- [[lead_time_days]] — the add-on only renders above 60 days <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 rule=[[addon-eligibility]] -->
```

A wikilink, one line of reasoning, and the machine fields in an HTML comment so
Obsidian's reading view stays clean. Declare it on either endpoint or both — the
parser unions them; only contradictory metadata is an error.

**The reasoning line is not decoration.** It is what a future session uses to
decide whether the edge still holds. "Confounder" is useless. "Reps call the
accounts they expect to convert" is the whole argument.

## What makes a good edge

- **A mechanism you can state.** If you cannot say how A moves B, you have a
  correlation, not an edge.
- **A rule, wherever one exists.** A documented threshold is the strongest edge
  available: deterministic, verifiable, and it explains the assignment.
- **Direction from timing.** If B is recorded before A, B does not cause A.

## What to leave out

- Edges added to make identification succeed. If you find yourself reaching for
  a mediator so a frontdoor argument works, stop — a refusal is the honest
  output and it names a design that would work instead.
- Everything correlated with everything. A graph that says all things affect all
  things identifies nothing and is not a claim.
- Nodes for columns nobody has a question about.

## Unobserved nodes

Write a file for the thing you cannot measure, with `observed: false`, and
explain in prose why it is not recorded and why no proxy works. This is what
lets a refusal name something concrete instead of shrugging. See
`wiki/graph/sales_rep_effort.md`.

## Several graphs

Node frontmatter carries `graphs: [name, ...]`, and that list is the only source
of membership — there is no manifest to fall out of sync. Keep areas separate so
you do not end up with one unreadable blob; a variable that genuinely appears in
two areas belongs to both.
