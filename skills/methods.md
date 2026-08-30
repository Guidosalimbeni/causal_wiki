# Suggesting a method

Identification passed and named a strategy. Now choose how to estimate — and
this is deliberately not a fixed menu, because causal inference is large and you
know more of it than could usefully be listed here.

## Read `wiki/methods/` first

```
cb methods                          # what has been used here, and how often
cb find "<method or subject>"       # notes, interviews, past questions, results
cb sql "SELECT method, treatment_kind, verdict, effect, finding FROM questions
        WHERE method <> '' ORDER BY id"
```

Search all three: the method notes, the *questions already answered* — their
interviews and write-ups are indexed too — and the experiments. What worked on
the last treatment of this kind is the strongest evidence available about what
will work on this one, and it is in the wiki rather than in your training.

The folder holds **both halves of the craft**: ways of estimating from data
that exists — IV, DiD, weighting, synthetic control, interrupted time series —
and ways of *creating* the data, which is to say designs. A/B tests, holdouts,
switchbacks, stepped-wedge rollouts, multi-arm bandits, encouragement designs.
A design is a method here, and gets a note like any other.

You already know all of them; that is not what the folder is for. It holds the part that is nowhere in
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

## Randomisation is not the fallback

An experiment is the only design that needs no untestable assumption, so it
belongs in the conversation in three separate situations, not one:

1. **Nothing observational recovers the effect.** Then the design *is* the
   answer, and `cb identify` has already named it.
2. **The analyst asks for one.** "What if I want to run a test instead — give me
   the design and a notebook." Do it. Never argue them back towards the
   observational route because it is available.
3. **The effect was identified and estimated.** Then propose the experiment that
   would confirm it. Two designs resting on different assumptions agreeing is
   worth far more than either alone — the toy example's holdout and its weighted
   estimate landing 0.3pp apart is the strongest claim in that wiki.

```
cb notebook new <qid> --design
```

Scaffolds power, assignment, the checks that catch a broken test, and a
pre-registered analysis plan. It works whatever the verdict was. Fill it in with
the analyst — the unit of randomisation, the exposure window and the guardrails
are business decisions and are not recoverable after the fact.

Then record it on the question, or it will be forgotten:

```yaml
design: 10% holdout of eligible accounts, rep calls suppressed for six weeks
design_status: proposed    # proposed | agreed | running | ran | declined
```

`cb gaps` lists proposed designs that never came back, and refusals with no
design recorded at all. When it runs, write it up in `wiki/experiments/` and set
`experiment:` on the record — `cb doctor` checks that the note exists.

`wiki/methods/` is where the *design type* accretes — how this company
randomises, what its traffic supports, which guardrails are standing policy.
`wiki/experiments/` is the one that ran. Both, not either.

## Identification is a closed list. Estimation is not.

These are two different choices and conflating them is what makes this step
look smaller than it is.

**Identification** — what *licenses* an estimate — is whatever `cb identify`
returned: `backdoor`, `frontdoor`, `iv`, `general_adjustment`. That list is
short because it is DoWhy's, not because the field is. It tells you which
variables may enter and in what role, and it is a constraint, not a suggestion:
adjusting for a set identification did not license is how a wrong number gets
produced confidently.

- **backdoor / general_adjustment** — adjust for the named set. Adding "just to
  be safe" variables is not safe: an extra collider opens a path that was closed.
- **frontdoor** — two stages through the mediator, with the full-mediation
  assumption stated out loud where the analyst can disagree with it.
- **iv** — the exclusion restriction is an assumption the graph cannot verify
  for you. Check instrument strength before anything else.
- **empty adjustment set** — a plain comparison really is enough. Say why, so it
  does not look like an oversight.

**Estimation** — how you actually compute it under that licence — is wide open,
and you know the field. Regression and matching, IPW and doubly-robust, DML and
the EconML metalearners, causal forests, uplift models, Bayesian structural
models, DoWhy's own estimators and `dowhy.gcm`, CausalML, whatever fits. The
question decides: sample size, functional form, whether the effect is plausibly
constant, how much overlap there is, whether anyone needs a per-unit answer or
just an average.

Nothing above is a menu to pick from. It is a reminder of the shape of the
choice, and the right estimator is regularly one not named here.

## `cb identify` does not have a view on every design

Its vocabulary is conditional independence in a DAG over the observed nodes.
Whole families of causal inference rest on assumptions that vocabulary cannot
express, and a refusal is not evidence against them:

- **Difference-in-differences**, and its staggered-adoption and
  heterogeneity-robust variants — parallel trends, not conditional independence.
- **Synthetic control** and its augmented forms — a weighted donor pool
  reproducing the pre-period.
- **Regression discontinuity** at a policy cutoff — continuity of potential
  outcomes at the threshold. This company's rules have thresholds in them, which
  is exactly where to look.
- **Interrupted time series**, panel and fixed-effects designs, event studies.
- **Encouragement designs and LATE**, when the treatment itself cannot be
  assigned but a nudge towards it can.

If one of these fits, say so and argue the assumption on its merits with the
analyst. `NO_CRITERION_FOUND` means no graph-based criterion over the observed
nodes was found — it never meant no design exists, and treating it that way is
the dead end this tool exists to avoid.

Record what you used in `method:` regardless. The index does not care whether
the licence came from the graph.

## Precision is a separate axis from identification

CUPED and pre-period covariate adjustment, stratification and blocking, variance
reduction, winsorising, clustered or bootstrapped standard errors: none of these
change what is identified, and none of them fix a broken design. They change how
tight the answer is. Reach for them when the estimate is right but too wide to
act on — and for an experiment, decide them *before* it runs, in the design
notebook.

## Ask what shape of answer is wanted

"Does it work" and "who does it work for" are different estimands and want
different tools. An average treatment effect, the effect on the treated, a
per-unit CATE from a causal forest or an EconML learner, an uplift model built
to rank who to target, a dose-response curve, an effect that changes over time.
Get this from the analyst before choosing anything — a heterogeneity model
answering an ATE question is wasted work, and an average hiding a sign flip
between segments is worse than wasted.

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
