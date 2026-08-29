---
description: A question arrived from the business. Work it end to end.
---

The question: **$ARGUMENTS**

Any causal question is in scope — does X cause Y, what is driving a change in Y,
how should we design a test, is this even answerable. There is no fixed menu.

## 1. Open the record

```
cb ask "$ARGUMENTS"
```

Note the question id it prints.

## 2. Load what is already known

```
cb context <qid>
cb find "<key terms from the question>"
```

Read the rules and traps that touch this area, and any prior question on the
same subject. Arrive informed — that is the entire point of the wiki.

## 3. Critique the question, then interview

Follow `skills/critique.md`, then `skills/interview.md`. Ask one thing at a
time. Work towards the graph, how the question should actually be posed, and
whether you understand the situation well enough to proceed.

Write nodes and edges into `wiki/graph/` as you go, following `skills/edges.md`
— during the interview, not after. Confirm each edge with the analyst as you
add it; that is why there is no approval queue.

Save `questions/<qid>/interview.yaml`, then write `treatment:` and `outcome:`
into `question.md`.

## 4. Identify

```
cb identify <qid>
```

This is code, not judgement. Do not talk yourself past its verdict.

- `IDENTIFIED` → continue, using the strategy it names.
- `NEEDS_EXPANSION` → the outcome is an accounting identity. Re-pose against the
  components and start again from step 3.
- `NO_CRITERION_FOUND` / `NO_DIRECTED_PATH` → **refuse, and say what design
  would work.** The report already names it. Write it up (`skills/writeup.md`)
  and offer the design. A refusal is a real finding, not a failure.

If the verdict comes back `provisional`, tell the analyst which edges are
unconfirmed and get them confirmed.

## 5. Notebook

```
cb notebook new <qid>
```

Fill in the analysis following `skills/methods.md`. Adjust for exactly the set
identification licensed — no extras. Put the sanity checks before the estimate.
Hand it over to run where the data is.

## 6. When it comes back

```
cb result add <qid> <executed notebook>
```

Read it, then refine, re-run, or conclude. Write up what was found *and* what
was learned (`skills/writeup.md`), then `cb index`.

## Throughout

- Never dead-end. If the analyst asks for something unfamiliar, try it or hand
  over a notebook. Never argue the question was ill-posed instead of answering.
- Everything ends recorded, including questions abandoned and notebooks that
  failed. Those are the useful ones.
- A notebook run outside and brought back is completed work, not an error.
