# Writing up what was learned

Stage five. The notebook came back. Now the loop closes, and this is the step
that makes the tenth question cheaper than the first.

## Two different things get written

**What was found** goes on the question record: the estimate, its uncertainty,
the method, and the finding in one sentence a business reader would understand.

**What was learned** goes into the wiki, and it is the durable half:

- A join that turned out to be wrong → the table doc.
- A column that is not what its name says → its causal annotation.
- A rule nobody had written down → `wiki/rules/`.
- A mistake that would be easy to repeat → `wiki/traps/`.
- An edge the data confirmed or contradicted → the node file, with the
  reasoning updated and `confirmed_by` set to whoever agreed.

If the answer came out and the wiki is unchanged, look again. Something was
learned; it just has not been recorded.

## Closing the record

```
cb result add <qid> <executed notebook>
```

Then set the status and fill in `method`, `effect`, and `finding`, so the
DuckDB index can answer questions across everything ever asked. Set
`treatment_kind` too — it is what makes "which approaches have failed for this
kind of treatment" answerable.

## The runs that failed

A notebook that errored, a method that did not converge, an estimate too
imprecise to act on — record all of it. A system that only logs successes never
learns from them, and the failures are the ones that stop the same road being
walked twice.

An abandoned question needs `abandoned_reason`. The schema enforces it.

## If the result was a refusal

Write up the refusal properly. It is a real finding: it says this question
cannot be answered with the data as it stands, and it names the design that
would change that. That is more useful to the business than a number with a
caveat nobody reads — and the caveat is what people act on anyway.

Record what it would take. Next time someone asks, the answer is already there.

## Rebuild the index

```
cb index && cb gaps
```

The index is derived and disposable — rebuilt from the markdown every time, so
it can never drift from it. Run it after writing, and see what the write opened
up.
