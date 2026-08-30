---
id: propensity-score-weighting
label: Propensity score weighting
aliases:
- backdoor.propensity_score_weighting
- ipw
- inverse probability weighting
source: questions/q-0001-showing-flexible-dates-add-on
confirmed_by: guido
confirmed_at: 2026-08-29
---

The default for anything gated by [[addon-eligibility]]. The rule keys on
`lead_time_days` and `booking_value`, so the propensity model is a model of the
rule, and it fits almost too well — which is the problem, not the reassurance.

## How it has to be tailored here

- **Trim on overlap before estimating.** The eligibility threshold is sharp at
  60 days, so propensities pile up near 0 and 1 and a handful of bookings pick
  up weights in the hundreds. Trim at [0.05, 0.95] and report how many rows went.
- **Filter the outcome window first.** `cancelled_90d_flag` reads as a false
  zero for bookings under 90 days old. Weighting cannot fix a mismeasured
  outcome, and the bias runs the same direction as the effect.
- **Never adjust for `addon_purchased`.** It is downstream of the impression.
  See [[adjusting-for-post-treatment-columns]].
- **Check the balance table, not just the estimate.** Standardised differences
  after weighting are the only evidence the rule was actually modelled.

## When it is the wrong tool here

Near-deterministic assignment means no overlap and no estimate. If a rule is a
hard gate rather than a threshold on a continuous variable, weighting has
nothing to work with — reach for a discontinuity design around the cutoff, or
say plainly that a holdout is what would answer it.

## What it has agreed with

The [[2025-q3-addon-holdout]] experiment found 1.8pp by randomisation against
2.1pp here. Two designs agreeing is worth more than either alone, and that
comparison is the main reason to keep trusting this one.


<!-- cb:managed name=questions sha=2dbf1ae25a21 -->
## Questions that reached for this

- [q-0001](../../questions/q-0001-showing-flexible-dates-add-on/question.md) — `backdoor.propensity_score_weighting` — concluded · IDENTIFIED — Does showing the flexible-dates add-on actually reduce cancellations?
  Showing the add-on reduces 90-day cancellation by about 2 percentage points.
<!-- /cb:managed -->
