---
id: sales_rep_effort
label: How hard the rep worked the account
kind: variable
observed: false
measured: never
causal_role: confounder
graphs:
- rep_outreach
source: wiki/process/outbound-sales.md
confirmed_by: guido
confirmed_at: 2026-08-29
---

**Not measured anywhere.** The CRM records that a call happened, never how well
it was worked, and reps put their effort into the accounts they judge most
likely to convert.

That judgement is what makes this a confounder: it drives both whether a call
gets made and whether the account upgrades. No column in the warehouse proxies
it — activity counts measure quantity, not quality.

This node exists precisely so a refusal can name it.

## Causes
- [[rep_call_made]] — reps call the accounts they believe will convert <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 -->
- [[upgrade_purchased]] — a well-worked account upgrades whether or not this particular call landed <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 -->
