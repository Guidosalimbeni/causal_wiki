"""Queries over the derived index: what haven't we looked at, and what do we know?"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..config import Config

# A question neither concluded nor abandoned is normal for a fortnight; past
# that it has been forgotten. Ageing is what keeps this gap readable once
# several analysts each have work in flight.
STALLED_AFTER_DAYS = 14


@dataclass
class Gap:
    kind: str
    subject: str
    detail: str


def _connect(cfg: Config):
    import duckdb

    if not cfg.db.exists():
        raise FileNotFoundError(f"no index at {cfg.db}. Run `cb index` first.")
    return duckdb.connect(str(cfg.db), read_only=True)


GAP_QUERIES: list[tuple[str, str, str]] = [
    (
        "unconfirmed-edge",
        "An edge nobody has confirmed. It will make any verdict that rests on it provisional.",
        """SELECT source || ' -> ' || target,
                  COALESCE(NULLIF(reason,''), 'no reasoning recorded')
           FROM edges WHERE kind='causal' AND NOT confirmed ORDER BY 1""",
    ),
    (
        "isolated-node",
        "A variable with no causal edges at all — nothing can be asked about it yet.",
        """SELECT n.id, COALESCE(NULLIF(n.label,''), n.id)
           FROM nodes n
           WHERE NOT EXISTS (SELECT 1 FROM edges e
                             WHERE (e.source=n.id OR e.target=n.id))
           ORDER BY 1""",
    ),
    (
        "unobserved-node",
        "Unobserved — every question routed through it risks a refusal.",
        """SELECT id, COALESCE(NULLIF(label,''), id) FROM nodes WHERE NOT observed ORDER BY 1""",
    ),
    (
        "unannotated-table",
        "A table whose columns carry no causal annotation. No semantic layer records this, "
        "and its absence is the most common source of wrong analysis.",
        """SELECT DISTINCT d.ref, d.title FROM docs d
           WHERE d.kind='table' AND NOT EXISTS (
               SELECT 1 FROM columns_ c
               WHERE c.tbl=d.ref AND c.causal_role NOT IN ('','unspecified'))
           ORDER BY 1""",
    ),
    (
        "column-without-timing",
        "A column with no `measured` anchor — whether it is recorded before or after "
        "treatment decides if adjusting on it is control or collider bias.",
        """SELECT tbl || '.' || column_name, COALESCE(NULLIF(causal_role,''),'unspecified')
           FROM columns_ WHERE COALESCE(measured,'')='' AND status<>'retired'
             AND column_name NOT LIKE '%\\_id' ESCAPE '\\'
             AND column_name <> 'id'
           ORDER BY 1""",
    ),
    (
        "stalled-question",
        f"Untouched for over {STALLED_AFTER_DAYS} days and neither concluded nor abandoned. "
        f"Either finish it or record why it was dropped.",
        f"""SELECT id, question || '  [' || status || ', last touched '
                     || substr(last_activity, 1, 10) || ']'
           FROM questions
           WHERE status NOT IN ('concluded','abandoned')
             AND substr(last_activity, 1, 10)
                 < CAST(current_date - INTERVAL {STALLED_AFTER_DAYS} DAY AS VARCHAR)
           ORDER BY last_activity""",
    ),
    (
        "question-without-interview",
        "Asked but never interviewed — no context was captured for the next question.",
        """SELECT q.id, q.question FROM questions q
           WHERE NOT EXISTS (SELECT 1 FROM docs d WHERE d.kind='interview' AND d.ref=q.id)
           ORDER BY q.id""",
    ),
    (
        "abandoned-without-reason",
        "Abandoned with no reason recorded. These are the ones worth learning from.",
        """SELECT id, question FROM questions
           WHERE status='abandoned' AND COALESCE(abandoned_reason,'')='' ORDER BY id""",
    ),
]


def gaps(cfg: Config, kinds: list[str] | None = None) -> list[Gap]:
    con = _connect(cfg)
    try:
        found: list[Gap] = []
        for kind, detail, sql in GAP_QUERIES:
            if kinds and kind not in kinds:
                continue
            for subject, extra in con.execute(sql).fetchall():
                found.append(Gap(kind=kind, subject=str(subject), detail=str(extra or detail)))
        return found
    finally:
        con.close()


def find(cfg: Config, query: str, limit: int = 20) -> list[tuple[str, str, str, str]]:
    """Full-text search across interviews, questions, tables, experiments and traps."""
    con = _connect(cfg)
    try:
        try:
            con.execute("LOAD fts;")
            rows = con.execute(
                """SELECT kind, ref, title, path FROM (
                       SELECT *, fts_main_docs.match_bm25(doc_id, ?) AS score FROM docs
                   ) WHERE score IS NOT NULL ORDER BY score DESC LIMIT ?""",
                [query, limit],
            ).fetchall()
            if rows:
                return [tuple(str(c) for c in r) for r in rows]  # type: ignore[misc]
        except Exception:
            pass
        return _find_without_fts(con, query, limit)
    finally:
        con.close()


def _find_without_fts(con, query: str, limit: int) -> list[tuple[str, str, str, str]]:
    """Fallback when the FTS extension cannot be loaded — offline, usually.

    Scored per term rather than matched as one literal string: a two-word query
    is the common case, and a LIKE on the whole phrase finds nothing unless the
    words happen to be adjacent.
    """
    terms = [t for t in re.findall(r"[\w'-]+", query.lower()) if len(t) > 1] or [query.lower()]
    score = " + ".join(
        "CASE WHEN lower(title || ' ' || text) LIKE ? THEN 1 ELSE 0 END" for _ in terms
    )
    rows = con.execute(
        f"""SELECT kind, ref, title, path FROM (
                SELECT kind, ref, title, path, {score} AS hits FROM docs
            ) WHERE hits > 0 ORDER BY hits DESC, ref LIMIT ?""",
        [*(f"%{t}%" for t in terms), limit],
    ).fetchall()
    return [tuple(str(c) for c in r) for r in rows]  # type: ignore[misc]


def query(cfg: Config, sql: str) -> tuple[list[str], list[tuple]]:
    con = _connect(cfg)
    try:
        cur = con.execute(sql)
        return [d[0] for d in cur.description], cur.fetchall()
    finally:
        con.close()


def summary(cfg: Config) -> dict[str, int]:
    con = _connect(cfg)
    try:
        out = {}
        for table in ("nodes", "edges", "questions", "experiments", "columns_", "docs"):
            out[table.rstrip("_")] = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        return out
    finally:
        con.close()
