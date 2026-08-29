---
id: booking_value
label: Total booking value (GBP)
kind: variable
observed: true
table: fact_booking.total_value_gbp
measured: at_booking
causal_role: confounder
graphs:
- addon_uptake
source: raw/2026-08-semantic-layer.csv
confirmed_by: guido
confirmed_at: 2026-08-29
---

## Causes
- [[addon_shown]] — the same eligibility rule gates on value over 800 <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 rule=[[addon-eligibility]] -->
- [[churn_90d]] — higher-value trips are cancelled less <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 -->
