---
description: Read everything in raw/ and write it into the wiki.
---

Stage one: collecting. Nothing is being asked yet — this is building context.

1. Run `cb ingest`. It imports anything shaped like a schema export (refreshing
   only the managed regions, so hand-written annotations survive) and lists what
   needs judgement.
2. Read `skills/routing.md` and follow it for each listed file.
3. Read each file properly before writing anything about it.
4. Record `source:` on everything, pointing back at the file under `raw/`.
5. Run `cb doctor`, then `cb index`.

**Ingest writes no causal edges.** Facts, definitions, rules and history only.
The graph gets drawn in the interview. If a document makes a causal claim,
record it as an attributed claim in prose — that is not an edge.

Pay particular attention to business rules. A rule that decides who gets treated
is the assignment mechanism and therefore the confounding, and it is usually
recorded nowhere else in the company.

$ARGUMENTS
