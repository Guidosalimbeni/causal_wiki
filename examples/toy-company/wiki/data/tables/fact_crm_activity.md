---
id: fact_crm_activity
label: fact_crm_activity
kind: table
table: fact_crm_activity
source: raw/2026-08-semantic-layer.csv
columns:
- name: account_id
  type: string
  causal_role: unspecified
- name: call_flag
  type: boolean
  causal_role: unspecified
---

# fact_crm_activity

## Schema

<!-- cb:managed name=schema sha=d2db9e86650e source=raw/2026-08-semantic-layer.csv -->
| column | type | description |
| --- | --- | --- |
| `account_id` | string | Foreign key to dim_account |
| `call_flag` | boolean | At least one outbound call this quarter |
<!-- /cb:managed -->

## Causal annotations

_Is each column measured before or after the treatment? Is it a mediator, a collider, a proxy? No semantic layer records this, and its absence is the most common source of wrong analysis._

## Joins that work

## Filters you always need
