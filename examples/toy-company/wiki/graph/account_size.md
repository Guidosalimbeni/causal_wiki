---
id: account_size
label: Corporate account size (seats)
kind: variable
observed: true
table: dim_account.seat_count
measured: at_period_start
causal_role: confounder
graphs:
- rep_outreach
source: raw/2026-08-semantic-layer.csv
confirmed_by: guido
confirmed_at: 2026-08-29
---

## Causes
- [[rep_call_made]] — reps are targeted on the larger accounts first <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 -->
- [[upgrade_purchased]] — larger accounts upgrade more regardless of contact <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 -->
