---
id: q-0001
status: concluded
method: backdoor.propensity_score_weighting
treatment_kind: ui_impression
effect: '-2.1pp (95% CI -3.5 to -0.8)'
finding: Showing the add-on reduces 90-day cancellation by about 2 percentage points.
asked_by: guido
asked_on: '2026-08-29'
graph: addon_uptake
outcome:
- churn_90d
question: Does showing the flexible-dates add-on actually reduce cancellations?
slug: showing-flexible-dates-add-on
treatment:
- addon_shown
verdict: IDENTIFIED
---

# Does showing the flexible-dates add-on actually reduce cancellations?

## As asked

> Does showing the flexible-dates add-on actually reduce cancellations?

## How it should be posed

Effect of `addon_shown` — the impression, not the purchase — on `churn_90d`,
among bookings meeting the eligibility rule, 2026 H1.

## Findings

Adjusting for `lead_time_days` and `booking_value` — the two variables the
eligibility rule keys on — showing the add-on reduces 90-day cancellation by
**2.1pp (95% CI -3.5 to -0.8)**, n=48,221.

Consistent in direction and magnitude with the [[2025-q3-addon-holdout]]
experiment, which found 1.8pp by randomisation. Two designs agreeing is worth
more than either alone.

**Caveat that matters:** the placebo refutation could not run — too few treated
units in the placebo sample. The estimate stands on the adjustment argument
alone, so it is weaker than the holdout.

## What we learned

- `cancelled_90d_flag` reads as a false zero for bookings under 90 days old.
  Now recorded in the table doc as a filter you always need.
- The 2025 analysis adjusted for `addon_purchased` and found nothing. That is
  the mediator, and this is now written up in
  [[adjusting-for-post-treatment-columns]].
- Still open: whether checkout ever manually overrode the eligibility threshold.
