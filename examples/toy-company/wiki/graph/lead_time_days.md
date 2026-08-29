---
id: lead_time_days
label: Days between booking and travel
kind: variable
observed: true
table: fact_booking.lead_time_days
measured: at_booking
causal_role: confounder
graphs:
- addon_uptake
source: raw/2026-08-semantic-layer.csv
confirmed_by: guido
confirmed_at: 2026-08-29
---

## Causes
- [[addon_shown]] — eligibility rule: the add-on only renders above 60 days, so lead time decides who is treated <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 rule=[[addon-eligibility]] -->
- [[churn_90d]] — long-lead bookings are more considered and cancel less often <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 -->
