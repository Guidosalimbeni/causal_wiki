"""Queries over the derived index: what haven't we looked at, and what do we know?"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..config import Config


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
        "Neither concluded nor abandoned. Either finish it or record why it was dropped.",
        """SELECT id, question || '  [' || status || ']'
           FROM questions WHERE status NOT IN ('concluded','abandoned') ORDER BY id""",
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
                       SELECT *, fts_main_docs.match_bm25(ref, ?) AS score FROM docs
                   ) WHERE score IS NOT NULL ORDER BY score DESC LIMIT ?""",
                [query, limit],
            ).fetchall()
            if rows:
                return [tuple(str(c) for c in r) for r in rows]  # type: ignore[misc]
        except Exception:
            pass
        # Fallback when the FTS extension is unavailable offline.
        rows = con.execute(
            """SELECT kind, ref, title, path FROM docs
               WHERE lower(text) LIKE lower(?) OR lower(title) LIKE lower(?) LIMIT ?""",
            [f"%{query}%", f"%{query}%", limit],
        ).fetchall()
        return [tuple(str(c) for c in r) for r in rows]  # type: ignore[misc]
    finally:
        con.close()


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
