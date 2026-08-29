---
id: net_revenue
label: Net revenue after cancellations (GBP)
kind: metric
observed: true
measured: 90d_after_booking
causal_role: unspecified
graphs:
- addon_uptake
source: raw/2026-08-semantic-layer.csv
confirmed_by: guido
confirmed_at: 2026-08-29
---

`net_revenue = revenue x (1 - churn_90d)`.

This is an accounting identity, not a mechanism. It is exactly true and tells
you nothing about cause, which is why it lives under `## Computed from` and
never enters the causal graph. Asking for the causal effect of anything *on*
this node is a category error, and `cb identify` will say so rather than
certifying the arithmetic as a finding.

## Computed from
- [[revenue]] <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 -->
- [[churn_90d]] <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 -->


<!-- cb:managed name=questions sha=5a5234712449 -->
## Questions asked here

- [q-0003](../../questions/q-0003-what-effect-showing-add-net/question.md) — outcome · refused · NEEDS_EXPANSION — What is the effect of showing the add-on on net revenue?
<!-- /cb:managed -->
