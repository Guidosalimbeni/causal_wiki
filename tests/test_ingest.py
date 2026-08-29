"""Re-import must never wipe out what was added on top."""

from __future__ import annotations

import pytest

from cb.config import Config
from cb.ingest import parse_schema_export, run, write_table_doc
from cb.wiki import frontmatter, managed

EXPORT = """table,column,type,description
fact_booking,booking_id,string,Primary key
fact_booking,lead_time_days,integer,Days to departure
fact_booking,legacy_flag,boolean,Deprecated
"""


@pytest.fixture
def project(tmp_path):
    cfg = Config(root=tmp_path)
    for d in cfg.dirs():
        d.mkdir(parents=True, exist_ok=True)
    (cfg.raw / "export.csv").write_text(EXPORT)
    return cfg


def annotate(cfg):
    """Stand in for the analyst doing the valuable part by hand."""
    path = cfg.tables_dir / "fact_booking.md"
    doc = frontmatter.load(path)
    for col in doc.meta["columns"]:
        if col["name"] == "lead_time_days":
            col["causal_role"] = "confounder"
            col["measured"] = "at_booking"
            col["note"] = "Gates eligibility AND drives churn."
    doc.body = doc.body.replace(
        "## Joins that work", "## Joins that work\n\nJoin on booking_id, never email."
    )
    doc.save(path)
    return path


class TestReimport:
    def test_annotations_survive_a_reimport(self, project):
        run(project)
        path = annotate(project)
        before = path.read_text()

        (project.raw / "export.csv").write_text(
            EXPORT.replace("Days to departure", "Days to departure (recomputed)")
        )
        run(project)

        doc = frontmatter.load(path)
        col = next(c for c in doc.meta["columns"] if c["name"] == "lead_time_days")
        assert col["causal_role"] == "confounder"
        assert col["measured"] == "at_booking"
        assert col["note"] == "Gates eligibility AND drives churn."
        assert "Join on booking_id, never email." in doc.body
        assert before != path.read_text()  # the managed region did change

    def test_human_prose_is_byte_identical_after_reimport(self, project):
        run(project)
        path = annotate(project)
        human_before = managed.human_text(frontmatter.load(path).body)

        (project.raw / "export.csv").write_text(EXPORT + "fact_booking,new_col,string,Added\n")
        run(project)

        assert managed.human_text(frontmatter.load(path).body) == human_before

    def test_a_dropped_column_is_retired_not_deleted(self, project):
        run(project)
        path = project.tables_dir / "fact_booking.md"

        (project.raw / "export.csv").write_text(
            "\n".join(l for l in EXPORT.splitlines() if "legacy_flag" not in l) + "\n"
        )
        run(project)

        col = next(
            c for c in frontmatter.load(path).meta["columns"] if c["name"] == "legacy_flag"
        )
        assert col["status"] == "retired"

    def test_a_returning_column_is_un_retired(self, project):
        run(project)
        reduced = "\n".join(l for l in EXPORT.splitlines() if "legacy_flag" not in l) + "\n"
        (project.raw / "export.csv").write_text(reduced)
        run(project)
        (project.raw / "export.csv").write_text(EXPORT)
        run(project)

        col = next(
            c
            for c in frontmatter.load(project.tables_dir / "fact_booking.md").meta["columns"]
            if c["name"] == "legacy_flag"
        )
        assert "status" not in col

    def test_a_new_column_is_added_unannotated(self, project):
        run(project)
        (project.raw / "export.csv").write_text(EXPORT + "fact_booking,refund,decimal,Refund\n")
        run(project)
        col = next(
            c
            for c in frontmatter.load(project.tables_dir / "fact_booking.md").meta["columns"]
            if c["name"] == "refund"
        )
        assert col["causal_role"] == "unspecified"

    def test_ingest_writes_no_causal_edges(self, project):
        """The fix for the review queue: facts only, never a causal claim."""
        (project.raw / "notes.md").write_text(
            "We think the discount drives retention. Reps target big accounts."
        )
        run(project)
        assert not list(project.graph_dir.rglob("*.md"))

    def test_unrecognised_files_are_returned_for_routing(self, project):
        (project.raw / "notes.md").write_text("prose, not a schema")
        _, needs_routing = run(project)
        assert [r.path.name for r in needs_routing] == ["notes.md"]

    def test_an_unchanged_file_is_not_reprocessed(self, project):
        run(project)
        written, _ = run(project)
        assert written == []


class TestSchemaDetection:
    def test_csv(self, tmp_path):
        p = tmp_path / "x.csv"
        p.write_text(EXPORT)
        assert len(parse_schema_export(p)["fact_booking"]) == 3

    def test_nested_yaml(self, tmp_path):
        p = tmp_path / "x.yaml"
        p.write_text(
            "tables:\n  orders:\n    columns:\n"
            "      - {name: id, type: string}\n      - {name: total, type: decimal}\n"
        )
        assert [c["name"] for c in parse_schema_export(p)["orders"]] == ["id", "total"]

    def test_prose_is_not_a_schema(self, tmp_path):
        p = tmp_path / "x.md"
        p.write_text("Just some notes about the business.")
        assert parse_schema_export(p) == {}


class TestManagedRegions:
    def test_only_the_region_is_replaced(self):
        text = "before\n\n" + managed.render("old", name="schema") + "\n\nafter\n"
        out = managed.replace(text, "new", name="schema")
        assert "before" in out and "after" in out
        assert "new" in out and "old" not in out

    def test_replacing_is_idempotent(self):
        text = managed.render("x", name="schema")
        assert managed.replace(managed.replace(text, "y", name="schema"), "y", name="schema") == \
               managed.replace(text, "y", name="schema")

    def test_human_text_excludes_the_region(self):
        text = "human\n\n" + managed.render("generated", name="schema") + "\n\nmore human\n"
        assert "generated" not in managed.human_text(text)
        assert "human" in managed.human_text(text)
