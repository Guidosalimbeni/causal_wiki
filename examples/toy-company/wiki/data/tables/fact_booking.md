---
id: fact_booking
label: fact_booking
kind: table
table: fact_booking
source: raw/2026-08-semantic-layer.csv
columns:
- name: booking_id
  type: string
  causal_role: unspecified
- name: lead_time_days
  type: integer
  causal_role: confounder
  measured: at_booking
  note: Gates add-on eligibility AND drives churn. Must be adjusted for.
- name: total_value_gbp
  type: decimal
  causal_role: confounder
  measured: at_booking
  note: The other half of the eligibility rule.
- name: addon_impression_flag
  type: boolean
  causal_role: treatment
  measured: at_quote
  note: What the business controls. Assigned by [[addon-eligibility]].
- name: addon_purchased_flag
  type: boolean
  causal_role: mediator
  measured: at_checkout
  note: POST-TREATMENT. Never adjust for this when asking about the impression.
- name: cancelled_90d_flag
  type: boolean
  causal_role: outcome
  measured: 90d_after_booking
  note: Only complete for bookings older than 90 days — always filter.
- name: gross_revenue_gbp
  type: decimal
  causal_role: unspecified
  measured: at_booking
  note: Feeds net_revenue through an identity, not a mechanism.
- name: legacy_promo_code
  type: string
  causal_role: unspecified
  status: retired
- name: refund_amount_gbp
  type: decimal
  causal_role: unspecified
---

# fact_booking

## Schema

<!-- cb:managed name=schema sha=7147477d18ff source=raw/2026-08-semantic-layer.csv -->
| column | type | description |
| --- | --- | --- |
| `booking_id` | string | Primary key |
| `lead_time_days` | integer | Days from booking to departure (recomputed 2026-08) |
| `total_value_gbp` | decimal | Total booking value including extras |
| `addon_impression_flag` | boolean | Whether the flexible-dates add-on was rendered |
| `addon_purchased_flag` | boolean | Whether the customer bought the add-on |
| `cancelled_90d_flag` | boolean | Cancelled within 90 days of booking |
| `gross_revenue_gbp` | decimal | Gross revenue recognised at booking |
| `refund_amount_gbp` | decimal | Refunded amount if cancelled |
<!-- /cb:managed -->

## Causal annotations

_Is each column measured before or after the treatment? Is it a mediator, a collider, a proxy? No semantic layer records this, and its absence is the most common source of wrong analysis._

The two that matter most here:

- `addon_impression_flag` is the **treatment**. It is assigned deterministically
  by [[addon-eligibility]], so that rule is the whole confounding story.
- `addon_purchased_flag` is **post-treatment** and a mediator. Adjusting for it
  while asking about the impression is what went wrong in 2025 — see
  [[adjusting-for-post-treatment-columns]].

## Joins that work

`fact_booking.booking_id` is unique. Join to `dim_account` through
`fact_booking.account_id`, never through the email field — it is not unique
across corporate bookings.

## Filters you always need

- `booked_at < now() - 90 days`, or `cancelled_90d_flag` is not yet observable
  and reads as a false zero.
- Exclude `channel = 'internal_test'`.
