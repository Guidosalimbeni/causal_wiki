# ⛔ Identification — q-0003

**Verdict:** `NEEDS_EXPANSION`

- **Treatment:** addon_shown
- **Outcome:** net_revenue
- **Graph:** addon_uptake

## What design would work

`net_revenue` is defined as an identity over `revenue`, `churn_90d`. An identity is exactly true and carries no causal content, so the effect on it is not a causal quantity. Re-pose the question against the components listed above — ask about each separately, then recombine through the identity if a headline number is wanted.

## Notes

- Arithmetic edges are excluded from the causal graph by construction.
