# Suggesting a method

Identification passed and named a strategy. Now choose how to estimate — and
this is deliberately not a fixed menu, because causal inference is large and you
know more of it than could usefully be listed here.

## Read `wiki/methods/` first

```
cb methods                # what has been used here, and how often
cb find "<method name>"   # where it was used, and what came of it
```

You already know IV, DiD, synthetic control, interrupted time series and the
rest; that is not what the folder is for. It holds the part that is nowhere in
your training: how each of them had to be bent to fit *this* business. Which
instrument survived scrutiny and which one an analyst demolished in a sentence.
Which window the billing cycle forces. Why the obvious cohort definition is
unavailable. What broke last time.

Methods repeat far more than questions do. A company that has settled on a
weighting approach for anything gated by an eligibility rule will use it again
next month, and arriving already knowing its trimming rule is the difference
between this and a textbook recommendation.

Bring it into the conversation with the analyst. They are the ones who know
whether last time's tailoring still holds.

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

## Then write the method up, not the textbook

If the method needed any local judgement — and it always does — it belongs in
`wiki/methods/<slug>.md`. `cb gaps` lists the ones used with nothing written
down.

```markdown
---
id: propensity-score-weighting
label: Propensity score weighting
aliases: [backdoor.propensity_score_weighting, ipw] # what `method:` might say
source: questions/q-0007-addon-churn
confirmed_by: guido
---

## How it has to be tailored here
## When it is the wrong tool here
## What it has agreed with
```

Write only what is specific to this company. "IPW reweights units by the inverse
of their propensity" is in every textbook and helps nobody; "trim at [0.05, 0.95]
because the eligibility threshold is sharp at 60 days and a handful of bookings
otherwise carry weights in the hundreds" is the whole value of the folder.

Add to an existing note rather than starting a near-duplicate. These accrete:
the fourth question to use a method is where the note gets good.

**Not the same as an experiment.** `wiki/experiments/` records one thing that was
run and what it found — a claim with a date on it. A method note is standing
guidance on how to estimate here, and it outlives any single question.
