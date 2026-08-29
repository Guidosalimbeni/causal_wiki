---
id: addon_purchased
label: Flexible-dates add-on purchased
kind: variable
observed: true
table: fact_booking.addon_purchased_flag
measured: at_checkout
causal_role: mediator
graphs:
- addon_uptake
source: raw/2026-08-semantic-layer.csv
confirmed_by: guido
confirmed_at: 2026-08-29
---

Measured *after* [[addon_shown]]. Adjusting for it when asking about the
impression would be conditioning on a mediator and would remove most of the
effect you are trying to measure. See [[adjusting-for-post-treatment-columns]].

## Caused by
- [[addon_shown]] <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 -->

## Causes
- [[churn_90d]] — a customer who paid for flexibility rebooks instead of cancelling <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 -->
- [[revenue]] — the add-on is charged at booking <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 -->
