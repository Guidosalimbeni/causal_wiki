# Suggesting a method

Identification passed and named a strategy. Now choose how to estimate — and
this is deliberately not a fixed menu, because causal inference is large and you
know more of it than could usefully be listed here.

## Start from what identification licensed

`identification.json` names the strategy and the variables. That constraint is
not a suggestion: adjusting for a set that identification did not license is how
a wrong number gets produced confidently.

- **backdoor** — regression, matching, IPW, doubly-robust, or a causal forest for
  heterogeneity. Adjust for the named set. Adding "just to be safe" variables is
  not safe: an extra collider opens a path that was closed.
- **frontdoor** — two stages through the mediator, with the full-mediation
  assumption stated out loud where the analyst can disagree with it.
- **iv** — 2SLS and its relatives. Check instrument strength, and remember the
  exclusion restriction is an assumption the graph cannot verify for you.
- **empty adjustment set** — a plain comparison really is enough. Say why, so it
  does not look like an oversight.

## Then think about the data, which the graph knows nothing about

The graph says an effect is recoverable in principle. Whether it is recoverable
from this table is a separate question: overlap, sample size, missingness,
clustering, seasonality, and how the outcome window interacts with the filters
the wiki says you always need.

Put those checks in the notebook *before* the estimate, not after.

## If the analyst asks for something specific

Try it. If they say `dowhy.gcm`, or a method you have not used, or something
that seems like the wrong tool — use it, or hand over a notebook that does.

**Never argue the question was ill-posed instead of answering.** That is the
worst failure mode available and it has happened before. If you think the
approach is wrong, run it *and* say why you would also do something else, with
both in the notebook. Disagreeing while delivering is fine. Refusing to deliver
because you disagree is not.

## Sensitivity is part of the answer

Every observational estimate rests on an assumption that could be false. An
E-value, a Rosenbaum bound, a negative control, or a placebo outcome turns "we
assumed no unmeasured confounding" into "it would take a confounder this strong
to overturn this". Include one by default.

## Record it

Put the method on the question record so the next person can query it:

```
cb sql "SELECT method, verdict, count(*) FROM effects GROUP BY 1,2"
```

"Which approaches have failed for this kind of treatment" is a query, not a
read. It only works if this gets filled in — including when the answer was that
the method did not work.
