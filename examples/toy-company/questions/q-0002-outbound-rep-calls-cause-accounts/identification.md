# ⛔ Identification — q-0002

**Verdict:** `NO_CRITERION_FOUND`

- **Treatment:** rep_call_made
- **Outcome:** upgrade_purchased
- **Graph:** rep_outreach
- **Unobserved in scope:** sales_rep_effort

## What blocks identification

- `sales_rep_effort` — unobserved, on a path that cannot be blocked

## What design would work

`sales_rep_effort` is an unobserved common cause of `rep_call_made` and `upgrade_purchased`, and no observed set blocks the backdoor path it opens.
Designs that would work, in rough order of cost:
1. **Measure `sales_rep_effort`.** If a proxy exists in the warehouse, add it as a node and re-run — a good proxy may close the path.
2. **Randomise `rep_call_made`.** An experiment removes every backdoor path by construction and is the only design that needs no further assumptions. `cb notebook new <qid> --design` scaffolds one.
3. **Find an instrument** — something that shifts `rep_call_made`, is unrelated to `upgrade_purchased` except through `rep_call_made`, and is already recorded. A policy threshold, a rollout date or a capacity constraint is often one.
4. **Find a full mediator** — a measured variable that carries the entire effect of `rep_call_made` on `upgrade_purchased`, which makes a frontdoor argument available.
5. **Use a design whose assumptions this graph cannot express.** Difference-in-differences, synthetic control, a regression discontinuity at a policy cutoff, an interrupted time series: these rest on parallel trends or continuity, not on conditional independence, so nothing above was ever a test of them. This verdict is about graph-based criteria over the observed nodes and says nothing against them — argue the assumption on its merits with the analyst instead.
