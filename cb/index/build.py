"""The DuckDB index — derived, disposable, never authoritative.

Markdown frontmatter is the only thing anyone writes. This file is dropped and
rebuilt from the wiki on every `cb index`, which is why "re-importing must never
wipe out what was added on top" cannot be violated here: there is nothing to
wipe out, and nothing to reconcile.

It earns its place because the wiki stops being navigable somewhere past fifty
entries, and "which approaches have failed for this kind of treatment" is a
query, not a read.
"""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from ..records import question as qmod
from ..records.interview import load as load_interview
from ..ingest import ANNOTATION_PROMPT
from ..wiki import frontmatter, graph as wikigraph, managed

SCHEMA = """
DROP TABLE IF EXISTS nodes;
DROP TABLE IF EXISTS edges;
DROP TABLE IF EXISTS questions;
DROP TABLE IF EXISTS effects;
DROP TABLE IF EXISTS experiments;
DROP TABLE IF EXISTS columns_;
DROP TABLE IF EXISTS docs;

CREATE TABLE nodes (
    id TEXT PRIMARY KEY, label TEXT, observed BOOLEAN, causal_role TEXT,
    tbl TEXT, measured TEXT, graphs TEXT, source TEXT,
    confirmed_by TEXT, confirmed_at TEXT, path TEXT
);
CREATE TABLE edges (
    source TEXT, target TEXT, kind TEXT, reason TEXT,
    confirmed_by TEXT, confirmed_at TEXT, confirmed BOOLEAN, declared_in TEXT
);
CREATE TABLE questions (
    id TEXT PRIMARY KEY, slug TEXT, question TEXT, asked_by TEXT, asked_on TEXT,
    last_activity TEXT, status TEXT, graph TEXT, treatment TEXT, outcome TEXT,
    treatment_kind TEXT, verdict TEXT, method TEXT, effect TEXT, finding TEXT,
    abandoned_reason TEXT, dir TEXT
);
CREATE TABLE effects (
    question_id TEXT, treatment TEXT, outcome TEXT, method TEXT,
    verdict TEXT, effect TEXT, finding TEXT
);
CREATE TABLE experiments (
    id TEXT, title TEXT, ran_on TEXT, treatment TEXT, outcome TEXT,
    finding TEXT, source TEXT, path TEXT
);
CREATE TABLE columns_ (
    tbl TEXT, column_name TEXT, causal_role TEXT, measured TEXT,
    status TEXT, note TEXT, path TEXT
);
CREATE TABLE docs (
    doc_id TEXT, kind TEXT, ref TEXT, title TEXT, text TEXT, path TEXT
);
"""


class _Docs:
    """Insert into `docs`, handing every row a unique id.

    DuckDB's FTS index keys on one column and needs it unique: a question and
    its interview share a `ref`, which silently broke `match_bm25` and dropped
    every search back to the LIKE fallback. The id is what makes ranked search
    work at all.
    """

    def __init__(self, con) -> None:
        self.con = con
        self.seen: set[str] = set()

    def add(self, kind: str, ref: str, title: str, text: str, path) -> None:
        doc_id = f"{kind}:{ref}"
        if doc_id in self.seen:
            n = 2
            while f"{doc_id}#{n}" in self.seen:
                n += 1
            doc_id = f"{doc_id}#{n}"
        self.seen.add(doc_id)
        self.con.execute(
            "INSERT INTO docs VALUES (?,?,?,?,?,?)",
            [doc_id, kind, ref, title, text, str(path)],
        )


def _join(value) -> str:
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(v) for v in value)
    return "" if value is None else str(value)


def build(cfg: Config) -> Path:
    import duckdb

    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    if cfg.db.exists():
        cfg.db.unlink()  # rebuilt from scratch every time, by design

    con = duckdb.connect(str(cfg.db))
    try:
        con.execute(SCHEMA)
        docs = _Docs(con)
        _index_graph(con, cfg)
        _index_questions(con, cfg, docs)
        _index_tables(con, cfg, docs)
        _index_prose(con, cfg, docs)
        _index_fts(con)
    finally:
        con.close()
    return cfg.db


def _index_graph(con, cfg: Config) -> None:
    if not cfg.graph_dir.exists():
        return
    wiki = wikigraph.load(cfg.graph_dir)
    for node in wiki.nodes.values():
        con.execute(
            "INSERT INTO nodes VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [
                node.id,
                node.label,
                node.observed,
                node.causal_role,
                str(node.meta.get("table", "")),
                str(node.meta.get("measured", "")),
                _join(node.graphs),
                str(node.meta.get("source", "")),
                str(node.meta.get("confirmed_by", "")),
                str(node.meta.get("confirmed_at", "")),
                str(node.path or ""),
            ],
        )
    for edge in wiki.edges.values():
        con.execute(
            "INSERT INTO edges VALUES (?,?,?,?,?,?,?,?)",
            [
                edge.source,
                edge.target,
                edge.kind,
                edge.reason,
                edge.confirmed_by,
                edge.confirmed_at,
                edge.confirmed,
                edge.declared_in,
            ],
        )


def _index_questions(con, cfg: Config, docs: _Docs) -> None:
    for q in qmod.iter_questions(cfg.questions):
        con.execute(
            "INSERT INTO questions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                q.id, q.slug, q.question, q.asked_by, q.asked_on, q.last_activity,
                q.status.value, q.graph or "", _join(q.treatment), _join(q.outcome),
                q.treatment_kind or "", q.verdict or "", q.method or "", q.effect or "",
                q.finding or "", q.abandoned_reason or "", str(q.dir or ""),
            ],
        )
        if q.verdict or q.effect or q.finding:
            con.execute(
                "INSERT INTO effects VALUES (?,?,?,?,?,?,?)",
                [q.id, _join(q.treatment), _join(q.outcome), q.method or "",
                 q.verdict or "", q.effect or "", q.finding or ""],
            )
        # The interview is searched by future questions — that is its whole point.
        if q.interview_path.exists():
            try:
                interview = load_interview(q.interview_path)
            except Exception:
                continue
            docs.add("interview", q.id, q.question, interview.searchable_text(),
                     q.interview_path)
        docs.add("question", q.id, q.question, f"{q.question}\n{q.body}", q.path)


def _index_tables(con, cfg: Config, docs: _Docs) -> None:
    """Column-level causal annotations — the most valuable thing in the wiki."""
    if not cfg.tables_dir.exists():
        return
    for path in sorted(cfg.tables_dir.rglob("*.md")):
        doc = frontmatter.load(path)
        table = str(doc.meta.get("table") or doc.meta.get("id") or path.stem)
        for col in doc.meta.get("columns") or []:
            if not isinstance(col, dict):
                continue
            con.execute(
                "INSERT INTO columns_ VALUES (?,?,?,?,?,?,?)",
                [
                    table, str(col.get("name", "")), str(col.get("causal_role", "")),
                    str(col.get("measured", "")), str(col.get("status", "active")),
                    str(col.get("note", "")), str(path),
                ],
            )
        # Index only what a human wrote: the generated schema block is already
        # in columns_, and the boilerplate prompt would match every query.
        text = managed.human_text(doc.body).replace(ANNOTATION_PROMPT, "")
        docs.add("table", table, str(doc.meta.get("label", table)), text, path)


def _index_prose(con, cfg: Config, docs: _Docs) -> None:
    for kind, directory in (
        ("experiment", cfg.experiments_dir),
        ("process", cfg.process_dir),
        ("trap", cfg.traps_dir),
        ("rule", cfg.rules_dir),
    ):
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*.md")):
            try:
                doc = frontmatter.load(path)
            except Exception:
                doc = frontmatter.Doc(meta={}, body=path.read_text(encoding="utf-8"))
            ref = str(doc.meta.get("id") or path.stem)
            title = str(doc.meta.get("label") or doc.meta.get("title") or ref)
            docs.add(kind, ref, title, doc.body, path)
            if kind == "experiment":
                con.execute(
                    "INSERT INTO experiments VALUES (?,?,?,?,?,?,?,?)",
                    [
                        ref, title, str(doc.meta.get("ran_on", "")),
                        _join(doc.meta.get("treatment")), _join(doc.meta.get("outcome")),
                        str(doc.meta.get("finding", "")), str(doc.meta.get("source", "")),
                        str(path),
                    ],
                )


def _index_fts(con) -> None:
    """DuckDB's own full-text search. No embeddings: they would need an API key,
    and FTS plus grep is ample below a few thousand documents."""
    try:
        con.execute("INSTALL fts; LOAD fts;")
        con.execute(
            "PRAGMA create_fts_index('docs', 'doc_id', 'title', 'text', overwrite=1);"
        )
    except Exception:
        # FTS is a convenience; `cb find` falls back to LIKE.
        pass
