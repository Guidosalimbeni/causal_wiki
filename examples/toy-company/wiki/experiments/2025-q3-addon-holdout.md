---
id: 2025-q3-addon-holdout
label: Q3 2025 add-on holdout test
kind: experiment
ran_on: 2025-08-11
treatment: addon_shown
outcome: churn_90d
finding: "Suppressing the add-on raised 90-day cancellation by 1.8pp (95% CI 0.4-3.2)."
source: raw/2025-q3-holdout-writeup.md
confirmed_by: guido
confirmed_at: 2026-08-29
---

# Q3 2025 add-on holdout

A 10% holdout of eligible bookings had the add-on suppressed for six weeks.

Because eligibility was held fixed and suppression was randomised *within* the
eligible population, [[addon-eligibility]] stopped being a confounder by
construction — the only design here that removes it without needing to model it.

## Finding

Cancellation within 90 days rose by 1.8pp in the holdout (95% CI 0.4 to 3.2).
Direction consistent with [[addon_purchased]] reducing [[churn_90d]].

## What it does not tell us

It ran only on the eligible population — lead time over 60 days and value over
GBP 800. It says nothing about what would happen if the rule were widened, which
is the question that keeps coming back. Extrapolating past the threshold is the
open problem.
