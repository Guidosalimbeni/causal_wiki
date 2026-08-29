---
description: Pick a question back up where it was left.
---

Question: **$ARGUMENTS** (if no id was given, run `cb status` and ask which one)

1. `cb status` — where everything stands.
2. `cb context <qid>` — the wiki as it now is.
3. Read `questions/<qid>/`: `question.md`, `interview.yaml`, `log.md`, and
   `identification.md` if it exists, plus anything under `results/`.

Then continue from the recorded status:

| status | next |
| --- | --- |
| `draft` / `interviewing` | continue the interview — `skills/interview.md` |
| `identified` | scaffold or fill in the notebook — `skills/methods.md` |
| `refused` | write up the refusal and the design that would work |
| `notebook` | it is with the analyst; ask if it has been run |
| `analysing` | read `results/`, then refine, re-run, or conclude |
| `concluded` / `abandoned` | done — say what was found, and offer the follow-on |

The wiki may have moved since this question was last touched. Re-run
`cb identify <qid>` before trusting an old verdict: an edge added for another
question can change this one, which is the point of keeping one shared graph.
