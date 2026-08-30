# Critiquing the question

The question as asked is rarely the question that can be answered. Run this
before identification — a well-posed question that gets refused is useful, a
badly-posed one that gets certified is dangerous.

## Is it causal at all?

Three different questions hide behind the same words:

- **Descriptive** — "what is churn among add-on buyers?" No graph needed. Answer
  it and move on; do not dress it up as causal.
- **Predictive** — "which bookings will cancel?" A model, not an intervention.
- **Causal** — "what happens to churn *if we change* who sees the add-on?"

Only the third needs any of this machinery. Say which one it is.

## Is the treatment something anyone can do?

If nobody can intervene on it, the effect may still be well defined but the
answer will not be actionable. "Does being a high-value customer cause loyalty"
has no intervention behind it. Push towards the decision actually being made.

Watch for the shown-versus-chosen split: the business usually controls the
*offer*, not the *uptake*. They are different treatments with different graphs
and different answers, and conflating them is the most common error here.

## Is the outcome a real quantity?

- Is it an accounting identity? `cb identify` catches this and returns
  `NEEDS_EXPANSION`, but noticing it in the interview is faster.
- Is it observable for everyone, or only for survivors? An outcome only recorded
  for customers who stayed builds selection into the question.
- Is the window stated? "Churn" without a horizon is not measurable.

## Is the population stated?

An effect is always an effect *among someone*. The Q3 holdout in the toy example
ran only on eligible bookings, so it says nothing about widening the rule — the
question people keep actually asking.

## Timing

For every variable in play: is it recorded before or after the treatment?
Anything after is a mediator or a collider, never a control. See
`wiki/traps/adjusting-for-post-treatment-columns.md`.

## The output

Restate the question in one sentence naming treatment, outcome, population and
period. If the analyst does not recognise it, you have not got it yet.

Also say whether the question could be settled by running something. "How
should we design a test for this" is a causal question in its own right and
arrives as often as "does X cause Y" — it goes through the same interview and
comes out as `cb notebook new <qid> --design`, not as a refusal.

Never respond to a badly-posed question by arguing it was ill-posed and
stopping. Re-pose it, offer the nearest answerable version, and carry on.
