---
id: dim_account
label: dim_account
kind: table
table: dim_account
source: raw/2026-08-semantic-layer.csv
columns:
- name: account_id
  type: string
  causal_role: unspecified
- name: seat_count
  type: integer
  causal_role: unspecified
---

# dim_account

## Schema

<!-- cb:managed name=schema sha=009a39345b18 source=raw/2026-08-semantic-layer.csv -->
| column | type | description |
| --- | --- | --- |
| `account_id` | string | Primary key |
| `seat_count` | integer | Contracted seats |
<!-- /cb:managed -->

## Causal annotations

_Is each column measured before or after the treatment? Is it a mediator, a collider, a proxy? No semantic layer records this, and its absence is the most common source of wrong analysis._

## Joins that work

## Filters you always need
