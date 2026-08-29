---
id: addon_shown
label: Flexible-dates add-on shown at checkout
kind: variable
observed: true
table: fact_booking.addon_impression_flag
measured: at_quote
causal_role: treatment
graphs:
- addon_uptake
source: raw/2026-08-semantic-layer.csv
confirmed_by: guido
confirmed_at: 2026-08-29
---

Whether the add-on was *rendered*, not whether it was bought. This is the
variable the business can actually intervene on: the rule that decides it is
[[addon-eligibility]], and that rule is the entire assignment mechanism.

## Caused by
- [[lead_time_days]] — rule threshold at 60 days <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 rule=[[addon-eligibility]] -->
- [[booking_value]] — rule threshold at GBP 800 <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 rule=[[addon-eligibility]] -->

## Causes
- [[addon_purchased]] — you cannot buy what you were never shown <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 -->
