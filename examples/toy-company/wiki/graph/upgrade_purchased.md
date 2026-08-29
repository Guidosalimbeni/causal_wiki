---
id: upgrade_purchased
label: Account upgraded to the premium tier
kind: variable
observed: true
table: fact_subscription.upgrade_flag
measured: end_of_quarter
causal_role: outcome
graphs:
- rep_outreach
source: raw/2026-08-semantic-layer.csv
confirmed_by: guido
confirmed_at: 2026-08-29
---

## Caused by
- [[rep_call_made]] <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 -->
- [[account_size]] <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 -->
- [[sales_rep_effort]] <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 -->


<!-- cb:managed name=questions sha=81d35796ff52 -->
## Questions asked here

- [q-0002](../../questions/q-0002-outbound-rep-calls-cause-accounts/question.md) — outcome · refused · NO_CRITERION_FOUND — Do outbound rep calls cause accounts to upgrade?
<!-- /cb:managed -->
