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


<!-- cb:managed name=questions sha=e07656f66909 -->
## Questions asked here

- [q-0001](../../questions/q-0001-showing-flexible-dates-add-on/question.md) — treatment · concluded · IDENTIFIED — Does showing the flexible-dates add-on actually reduce cancellations?
  Showing the add-on reduces 90-day cancellation by about 2 percentage points.
- [q-0003](../../questions/q-0003-what-effect-showing-add-net/question.md) — treatment · refused · NEEDS_EXPANSION — What is the effect of showing the add-on on net revenue?
<!-- /cb:managed -->
