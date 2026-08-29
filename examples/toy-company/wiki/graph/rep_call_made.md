---
id: rep_call_made
label: Outbound rep call made this quarter
kind: variable
observed: true
table: fact_crm_activity.call_flag
measured: during_quarter
causal_role: treatment
graphs:
- rep_outreach
source: raw/2026-08-semantic-layer.csv
confirmed_by: guido
confirmed_at: 2026-08-29
---

## Caused by
- [[account_size]] <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 -->
- [[sales_rep_effort]] <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 -->

## Causes
- [[upgrade_purchased]] — the question under test <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 -->
