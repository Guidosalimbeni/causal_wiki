# Toy Travel Co — causal wiki

The worked example that ships with `cb`. A small booking business: quotes, a
flexible-dates add-on shown under an eligibility rule, subscriptions, and an
outbound sales team.

**I am a causal analyst here, not a reporting one.** Every question is about an
effect, and the difference from correlation is the entire job.

- The add-on is shown by a **rule** keyed on `lead_time_days` and
  `booking_value` — see `wiki/rules/addon-eligibility.md`. That rule *is* the
  confounding. Anything comparing buyers to non-buyers without it is measuring
  who qualifies, not what the add-on does.
- `addon_purchased` is downstream of `addon_shown`. Adjusting for it when the
  question is about the impression removes the effect being measured. This has
  already happened once — `wiki/traps/`.
- `cancelled_90d_flag` reads as a false zero for bookings under 90 days old.
  Filter before estimating.
- `sales_rep_effort` is unobserved, which is why the outbound question refuses.
  A refusal naming the design that would work is the answer, not a failure.

## Try it

```bash
cb doctor              # the wiki is clean
cb identify q-0001     # IDENTIFIED — backdoor on the two rule variables
cb identify q-0002     # refused: NO_CRITERION_FOUND, and it names why
cb identify q-0003     # refused: NEEDS_EXPANSION, an accounting identity
cb methods             # how this company estimates things
```

Identification is `cb identify`, never my own reading of the graph. Read
`skills/` before acting; `wiki/methods/` before choosing how to estimate.
