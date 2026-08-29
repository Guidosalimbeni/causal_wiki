---
id: fact_subscription
label: fact_subscription
kind: table
table: fact_subscription
source: raw/2026-08-semantic-layer.csv
columns:
- name: account_id
  type: string
  causal_role: unspecified
- name: upgrade_flag
  type: boolean
  causal_role: unspecified
---

# fact_subscription

## Schema

<!-- cb:managed name=schema sha=4c4d027e65fa source=raw/2026-08-semantic-layer.csv -->
| column | type | description |
| --- | --- | --- |
| `account_id` | string | Foreign key to dim_account |
| `upgrade_flag` | boolean | Upgraded to premium during the quarter |
<!-- /cb:managed -->

## Causal annotations

_Is each column measured before or after the treatment? Is it a mediator, a collider, a proxy? No semantic layer records this, and its absence is the most common source of wrong analysis._

## Joins that work

## Filters you always need
