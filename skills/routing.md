# Routing ingested material

`cb ingest` has already imported anything shaped like a schema export and listed
what it could not. Your job is the rest: read each file and write what it says
into the wiki, with a link back to where it came from.

## The one hard rule

**Ingest never writes a causal edge.** Not "probably causes", not a suggestion,
not a pending item. Facts, definitions, rules and history only.

This exists because the alternative was tried: an approval queue where one
document produced twenty-nine pending items nobody ever reviewed, so nothing got
built. The graph gets drawn in the interview, where the analyst is answering
questions anyway, and approval is part of the conversation instead of a backlog.

If a document is *about* causal structure ("we think the discount drives
retention"), record it as a claim in prose — under a process or experiment note,
attributed to whoever said it. A claim in prose is not an edge.

## Where things go

| material | destination |
| --- | --- |
| table, column, join, filter | `wiki/data/tables/<table>.md`, human sections only |
| what a column *means* causally, when it is measured | the same file's `columns:` frontmatter and Causal annotations |
| "the add-on only shows when lead time > 60" | `wiki/rules/<slug>.md` — **and see below** |
| how the business works, in prose | `wiki/process/<slug>.md` |
| an old experiment and what it found | `wiki/experiments/<slug>.md` |
| a mistake that keeps getting made | `wiki/traps/<slug>.md` |
| a variable worth reasoning about | `wiki/graph/<id>.md` — nodes only, no edges yet |

## Business rules deserve more attention than they look like they need

A rule that decides who gets a treatment **is** the assignment mechanism, so it
**is** the confounding — and it is usually written down nowhere else in the
company. When you find one, write down the exact thresholds, when it changed,
and which variables it keys on. Then say plainly in the file which variables an
analysis would have to adjust for as a result.

`wiki/rules/addon-eligibility.md` in the toy example shows the shape.

## Always

- Record `source:` in frontmatter pointing at the file under `raw/`.
- Set `confirmed_by:` to the person who told you, not to yourself.
- If a claim contradicts something already in the wiki, do not overwrite it.
  Note both and raise it with the analyst.
- Prefer adding to an existing file over creating a new one. The wiki is
  organised for reading.
