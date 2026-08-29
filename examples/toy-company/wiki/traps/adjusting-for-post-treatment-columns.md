---
id: adjusting-for-post-treatment-columns
label: Adjusting for anything measured after the treatment
kind: trap
source: raw/2025-analysis-retro.md
confirmed_by: guido
confirmed_at: 2026-08-29
---

# Anything measured after the treatment is not a control

The warehouse gives every column the same shape, so `measured` is the only thing
that distinguishes a legitimate control from a mediator or a collider — and no
semantic layer records it. That is why every node file here carries a `measured`
anchor.

Two failure modes, both of which look like careful work:

- **Mediator.** Adjusting for something on the causal path removes the effect
  you are measuring. [[addon_purchased]] sits between [[addon_shown]] and
  [[churn_90d]]; controlling for it makes a real effect vanish.
- **Collider.** Adjusting for a common *consequence* of treatment and outcome
  creates an association where none existed. This one manufactures findings
  rather than hiding them, which makes it the more dangerous of the two.

The rule of thumb that has held up here: if you cannot say when a column is
written relative to the treatment, do not put it in the adjustment set.
