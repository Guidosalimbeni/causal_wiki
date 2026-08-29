---
id: addon-eligibility
label: When the flexible-dates add-on is shown
kind: rule
status: active
source: raw/checkout-rules-2026-03.md
confirmed_by: guido
confirmed_at: 2026-08-29
---

# Add-on eligibility

The flexible-dates add-on is rendered at checkout only when **both** hold:

- lead time is over **60 days**, and
- total booking value is over **GBP 800**.

Introduced March 2024. Unchanged since.

## Why this matters more than it looks

This rule **is** the assignment mechanism. It decides who gets treated, so it
**is** the confounding — and it is written down nowhere else in the company.

Anyone comparing customers who saw the add-on against customers who did not is
comparing long-lead high-value bookings against short-lead cheap ones. Those two
groups differ in exactly the ways that also drive cancellation, which is why the
naive difference in [[churn_90d]] is large and meaningless.

The good news is that the rule is deterministic and both inputs are recorded, so
adjusting for [[lead_time_days]] and [[booking_value]] closes the backdoor path
completely. Identification for [[addon_shown]] turns entirely on this fact.

## Related

- [[addon_shown]] — the variable the rule assigns
- [[naive-addon-churn-comparison]] — the trap this rule creates
