---
id: churn_90d
label: Booking cancelled within 90 days
kind: variable
observed: true
table: fact_booking.cancelled_90d_flag
measured: 90d_after_booking
causal_role: outcome
graphs:
- addon_uptake
source: raw/2026-08-semantic-layer.csv
confirmed_by: guido
confirmed_at: 2026-08-29
---

## Caused by
- [[addon_purchased]] — flexibility lets a customer move the date rather than cancel <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 -->
- [[lead_time_days]] <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 -->
- [[booking_value]] <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 -->
