---
id: naive-addon-churn-comparison
label: Comparing add-on buyers with everyone else
kind: trap
source: raw/2025-analysis-retro.md
confirmed_by: guido
confirmed_at: 2026-08-29
---

# The add-on churn comparison keeps getting made wrong

Asked three times now, wrong twice. Two distinct mistakes, both easy to make.

## 1. Ignoring the eligibility rule

[[addon-eligibility]] means the add-on is only ever shown to long-lead,
high-value bookings. Comparing those who saw it against those who did not is
comparing two different kinds of customer. Adjust for [[lead_time_days]] and
[[booking_value]] and the backdoor path closes.

## 2. Confusing "shown" with "purchased"

[[addon_shown]] is what the business controls. [[addon_purchased]] is a customer
choice, measured after, and a mediator. The 2025 analysis adjusted for
`addon_purchased` while asking about the impression and reported an effect near
zero — it had conditioned away the mechanism it was trying to measure. See
[[adjusting-for-post-treatment-columns]].

If the question is "should we keep showing it", the treatment is the impression.
