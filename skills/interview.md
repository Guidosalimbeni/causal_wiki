# The interview

This is the heart of the tool. A question has arrived and a record exists. Now
read the wiki and ask informed questions — informed because you already know the
tables, the rules, the process and what has been tried.

The interview is not a transcript to be filed away. Future questions search it,
so a good interview makes the next one shorter.

## Before you ask anything

```
cb context <qid>          # graphs, tables, rules, prior questions
cb find "<terms>"         # past interviews and findings on this subject
cb graph show <name>      # the edges as the parser actually reads them
```

Read the rules and traps files that touch the subject. Arriving already knowing
that the add-on is gated on lead time is the difference between this and a
generic questionnaire.

## What you are working towards

Three things, in this order:

1. **What the causal graph looks like** in this area — enough of it to identify
   against, not the whole business.
2. **How the question should actually be posed.** The question as asked is
   rarely the question that can be answered. "Does the add-on reduce churn"
   might mean the impression or the purchase, and those have different answers.
   See [critique.md](critique.md).
3. **Whether you now understand the situation well enough to proceed.** Say so
   explicitly. `ready: false` with a list of what is missing is a perfectly good
   outcome — it is what `cb gaps` is for.

## How to ask

- **One thing at a time.** A wall of questions gets a wall of half-answers.
- **Ask what only they know.** Not "is age a confounder" — that is your job.
  Ask "how does someone end up in this group in the first place?", because the
  answer is the assignment mechanism and it is usually undocumented.
- **Chase the timing.** For every variable, when is it recorded relative to the
  treatment? This is the single most common source of wrong analysis and no
  semantic layer records it.
- **Ask what would change their mind.** If nothing would, the question is not
  really being asked.
- **Prefer the mechanism to the correlation.** "What happens, step by step, when
  a customer sees this?" surfaces mediators and colliders that no amount of
  staring at column names will.

## Drawing the graph

Propose edges as you go and confirm them out loud — the analyst is right there,
which is exactly why there is no approval queue. Follow [edges.md](edges.md) for
the mechanics and the confirmation rules.

Write nodes and edges into `wiki/graph/` **during** the interview, not after.
The wiki is the working surface, not a report.

## Saving

Write `questions/<qid>/interview.yaml`:

```yaml
question_id: q-0007
posed_as: "Effect of addon_shown on churn_90d among eligible bookings, 2026 H1"
graph: addon_uptake
treatment: [addon_shown]
outcome: [churn_90d]
population: "Bookings meeting the eligibility rule"
period: "2026-01-01 to 2026-06-30"
turns:
  - asked: "How does a booking end up seeing the add-on?"
    answered: "There's a rule — lead time over 60 days and value over 800."
    established: "Assignment is deterministic on two recorded variables."
edges:
  - {source: lead_time_days, target: addon_shown, reason: "eligibility rule", confirmed: true}
assumptions:
  - "The rule has not changed during the period."
open_questions:
  - "Whether the threshold was ever manually overridden."
wiki_gaps:
  - "No node for the channel the booking came through."
ready: true
```

Then write `treatment:` and `outcome:` into `question.md` and run
`cb identify <qid>`.

## When the interview reveals there is no question

Sometimes the honest outcome is that the business is asking something
unanswerable, or something that is not causal at all. Record it — set the status
to `abandoned` with an `abandoned_reason`. The schema will not let you abandon
without one, because those are the records worth having.

That is not a dead end: say what *would* be answerable and offer it.
