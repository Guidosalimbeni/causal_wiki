"""Parser tests: the node files must mean what they look like they mean."""

from __future__ import annotations

import pytest

from cb.wiki import frontmatter, graph as wikigraph
from cb.wiki.nodes import UNCONFIRMED, parse, parse_edges

NODE = """---
id: addon_shown
label: Add-on shown
observed: true
graphs:
- addon_uptake
confirmed_by: guido
confirmed_at: 2026-08-29
---

Prose about the node, with a [[link]] that is not in a typed section.

## Caused by
- [[lead_time_days]] — rule threshold at 60 days <!-- cb: confirmed_by=guido confirmed_at=2026-08-29 rule=[[addon-eligibility]] -->
- [[booking_value]] — the other half of the rule

## Causes
- [[churn_90d]] — hypothesised <!-- cb: confirmed_by=claude-proposed -->

## Computed from
(none — arithmetic only)
"""


class TestFrontmatter:
    def test_round_trip_is_byte_identical(self):
        doc = frontmatter.loads(NODE)
        assert frontmatter.loads(doc.dump()).dump() == doc.dump()

    def test_body_is_preserved_verbatim(self):
        doc = frontmatter.loads(NODE)
        assert "## Caused by" in doc.body
        assert doc.body.startswith("Prose about the node")

    def test_a_body_containing_a_delimiter_is_safe(self):
        doc = frontmatter.loads("---\nid: x\n---\n\nbefore\n\n---\n\nafter\n")
        assert "before" in doc.body and "after" in doc.body

    def test_missing_frontmatter_is_an_error(self):
        with pytest.raises(frontmatter.FrontmatterError, match="does not start"):
            frontmatter.loads("# just a heading\n")

    def test_unclosed_frontmatter_is_an_error(self):
        with pytest.raises(frontmatter.FrontmatterError, match="never closed"):
            frontmatter.loads("---\nid: x\n")


class TestEdgeParsing:
    def setup_method(self):
        self.edges = parse_edges("addon_shown", frontmatter.loads(NODE).body)

    def test_heading_gives_the_direction(self):
        caused_by = next(e for e in self.edges if e.source == "lead_time_days")
        assert caused_by.target == "addon_shown"
        causes = next(e for e in self.edges if e.target == "churn_90d")
        assert causes.source == "addon_shown"

    def test_reasoning_is_kept_and_the_comment_stripped(self):
        edge = next(e for e in self.edges if e.source == "lead_time_days")
        assert edge.reason == "rule threshold at 60 days"
        assert "<!--" not in edge.reason

    def test_machine_fields_come_off_the_comment(self):
        edge = next(e for e in self.edges if e.source == "lead_time_days")
        assert edge.confirmed_by == "guido"
        assert edge.meta["rule"] == "[[addon-eligibility]]"
        assert edge.confirmed

    def test_an_edge_with_no_comment_is_unconfirmed(self):
        edge = next(e for e in self.edges if e.source == "booking_value")
        assert edge.confirmed_by == UNCONFIRMED
        assert not edge.confirmed

    def test_links_outside_a_typed_section_are_not_edges(self):
        assert not any("link" in (e.source, e.target) for e in self.edges)

    def test_a_prose_bullet_is_not_an_edge(self):
        assert not any(e.kind == "arithmetic" for e in self.edges)

    def test_arithmetic_is_a_separate_kind(self):
        edges = parse_edges("net_revenue", "## Computed from\n- [[revenue]]\n- [[churn]]\n")
        assert {e.kind for e in edges} == {"arithmetic"}
        assert all(e.target == "net_revenue" for e in edges)


class TestReconciliation:
    """An edge may be declared on either endpoint, or both."""

    def _load(self, tmp_path, a: str, b: str):
        (tmp_path / "a.md").write_text(f"---\nid: a\n---\n\n{a}\n")
        (tmp_path / "b.md").write_text(f"---\nid: b\n---\n\n{b}\n")
        return wikigraph.load(tmp_path)

    def test_declaring_from_both_sides_yields_one_edge(self, tmp_path):
        wiki = self._load(
            tmp_path,
            "## Causes\n- [[b]] — because <!-- cb: confirmed_by=guido -->",
            "## Caused by\n- [[a]] — because <!-- cb: confirmed_by=guido -->",
        )
        assert len(wiki.edges) == 1
        assert not wiki.conflicts
        assert wiki.causal().has_edge("a", "b")

    def test_contradictory_metadata_is_reported(self, tmp_path):
        wiki = self._load(
            tmp_path,
            "## Causes\n- [[b]] <!-- cb: confirmed_by=guido -->",
            "## Caused by\n- [[a]] <!-- cb: confirmed_by=someone_else -->",
        )
        assert len(wiki.conflicts) == 1
        assert wiki.conflicts[0].key == "confirmed_by"

    def test_asymmetry_alone_is_not_a_conflict(self, tmp_path):
        wiki = self._load(tmp_path, "## Causes\n- [[b]] — because", "")
        assert not wiki.conflicts
        assert wiki.causal().has_edge("a", "b")

    def test_a_link_to_a_missing_node_is_dangling(self, tmp_path):
        wiki = self._load(tmp_path, "## Causes\n- [[nowhere]]", "")
        assert [e.target for e in wiki.dangling] == ["nowhere"]


def test_named_graphs_come_only_from_frontmatter(tmp_path):
    (tmp_path / "a.md").write_text("---\nid: a\ngraphs: [one, two]\n---\n")
    (tmp_path / "b.md").write_text("---\nid: b\ngraphs: [two]\n---\n")
    wiki = wikigraph.load(tmp_path)
    assert wiki.graph_names() == ["one", "two"]
    assert wiki.view("one") == {"a"}
    assert wiki.view("two") == {"a", "b"}


def test_parse_rejects_an_unknown_causal_role(tmp_path):
    path = tmp_path / "x.md"
    path.write_text("---\nid: x\ncausal_role: vibes\n---\n")
    with pytest.raises(Exception, match="causal_role"):
        parse(path)
