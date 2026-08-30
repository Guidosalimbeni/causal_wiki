---
id: randomised-holdout
label: Randomised holdout
aliases:
- ab test
- a/b test
- holdout
- randomised experiment
kind: design
source: wiki/experiments/2025-q3-addon-holdout.md
confirmed_by: guido
confirmed_at: 2026-08-30
---

How this company runs a test. Suppress or withhold a treatment from a random
slice of an otherwise eligible population, rather than granting it to a random
slice of everyone — which matters here, because eligibility is itself a rule and
randomising across it changes the population instead of the treatment.

## How it has to be tailored here

- **Randomise inside the eligible set, never across it.** Holding
  [[addon-eligibility]] fixed and randomising suppression is what made the
  [[2025-q3-addon-holdout]] clean. Randomising who is *eligible* answers a
  different question, and it is usually not the one being asked.
- **Booking is the unit for anything in checkout; account for anything a rep
  touches.** Reps work a whole account, so assigning at booking level leaks
  treatment between arms through the rep. Assign at account level and pay for
  the clustering in the sample size.
- **Exposure window ≥ 6 weeks, outcome window 90 days on top.** Anything
  shorter and `churn_90d` is a false zero for most of the arm. The Q3 test ran
  six weeks and waited; that is the shape.
- **Sales can pull an account out of a holdout.** They have done it. Any
  suppression test needs the override log checked before the arms are trusted —
  a hand-picked exit from the control arm is not randomisation any more.
- **Guardrails are standing policy:** booking volume, refund rate, and rep
  quota attainment. Checked as decision rules, not ranked against the primary.

## When it is the wrong tool here

Suppressing something customers already have is a real cost and Finance has
refused it twice for anything revenue-bearing above the GBP 800 threshold. For
those, an encouragement design — randomise a nudge towards the treatment rather
than the treatment itself — is what has actually got approved, and it estimates
a local effect among compliers rather than the average one. Say which you are
getting before it runs.

## What it has agreed with

The Q3 holdout found 1.8pp against 2.1pp from
[[propensity-score-weighting]] on observational data. Two designs with different
assumptions landing 0.3pp apart is the strongest claim in this wiki, and it is
the reason the weighted estimate is still trusted for the questions no one will
randomise.


<!-- cb:managed name=questions sha=d6681d16b279 -->
## Questions that reached for this

- [q-0002](../../questions/q-0002-outbound-rep-calls-cause-accounts/question.md) — `Randomise rep calls at account level — a 6-week holdout on a random 10% of accou` — design proposed · refused — Do outbound rep calls cause accounts to upgrade?
<!-- /cb:managed -->
