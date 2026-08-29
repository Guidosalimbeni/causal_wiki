# Toy company

A complete `cb` project, small enough to read in ten minutes. Everything here is
invented, but the shapes are the ones that actually cause trouble.

```bash
cb doctor
cb graph list
cb identify q-0001   # IDENTIFIED
cb identify q-0002   # refused, names the unobserved node
cb identify q-0003   # re-posed: the outcome is an accounting identity
cb index && cb gaps
```

## Two graphs, kept apart

**`addon_uptake`** — a travel booking site. A flexible-dates add-on is shown at
checkout, but only when [lead time > 60 days and value > GBP 800](wiki/rules/addon-eligibility.md).

That rule **is** the assignment mechanism, so it **is** the confounding — and in
a real company it would be written down nowhere else. Both of its inputs are
recorded, so the backdoor path closes and `q-0001` identifies.

**`rep_outreach`** — outbound corporate sales. Reps choose which accounts to
work, and [the CRM records that a call happened but never how well it was worked](wiki/process/outbound-sales.md).
That judgement is [`sales_rep_effort`](wiki/graph/sales_rep_effort.md), marked
`observed: false`. It confounds both the call and the upgrade, no proxy exists,
and so `q-0002` is refused — naming the node and proposing randomisation.

## What each question demonstrates

| | | |
| --- | --- | --- |
| `q-0001` | `IDENTIFIED` | backdoor adjustment on the two variables the rule keys on; concluded with a finding, a caveat, and a failed refutation kept on the record |
| `q-0002` | `NO_CRITERION_FOUND` | an unobserved confounder with no design around it |
| `q-0003` | `NEEDS_EXPANSION` | `net_revenue` is an identity over `revenue` and `churn_90d`; the effect *on* it is a category error |

## Things worth looking at

- [`wiki/graph/net_revenue.md`](wiki/graph/net_revenue.md) — `## Computed from`,
  the edge kind that keeps an accounting identity out of the causal graph.
- [`wiki/data/tables/fact_booking.md`](wiki/data/tables/fact_booking.md) — a
  managed region holding the generated schema, with hand-written causal
  annotations around it that survive re-import. Note `legacy_promo_code`:
  retired upstream, kept here.
- [`wiki/traps/`](wiki/traps/) — the two mistakes this domain keeps producing.
- [`questions/q-0001-showing-flexible-dates-add-on/`](questions/) — all five
  stages hanging off one id, including the failed placebo refutation.
