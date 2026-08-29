---
id: revenue
label: Gross booking revenue (GBP)
kind: metric
observed: true
table: fact_booking.gross_revenue_gbp
measured: at_booking
causal_role: unspecified
graphs:
- addon_uptake
source: raw/2026-08-semantic-layer.csv
confirmed_by: guido
confirmed_at: 2026-08-29
---

## Caused by
- [[addon_purchased]] <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 -->
