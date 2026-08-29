"""Ingest: get raw material into the wiki with a link back to where it came from.

Split deliberately. The deterministic half lives here: inventory `raw/`, notice
what changed, and refresh the generated block of a table doc from a semantic
layer export. The judgement half — what a document means, where it belongs,
what it implies — is a skill.

Ingest never writes a causal edge. That is the fix for the review queue: one
document used to produce twenty-nine pending items nobody read, so nothing got
built. Facts land here; the graph gets drawn in the interview, where the analyst
is already answering questions.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .config import Config
from .wiki import frontmatter, managed

MANIFEST = "ingest.json"

# Boilerplate placed in every new table doc. Useful to a human reader, but it
# mentions "mediator", "collider" and "proxy", so left in the search index it
# makes every unannotated table match every query about those terms.
ANNOTATION_PROMPT = (
    "_Is each column measured before or after the treatment? Is it a mediator, a "
    "collider, a proxy? No semantic layer records this, and its absence is the most "
    "common source of wrong analysis._"
)

TABLE_KEYS = ("table", "table_name", "model", "dataset", "entity")
COLUMN_KEYS = ("column", "column_name", "field", "name", "dimension", "measure")
TYPE_KEYS = ("type", "data_type", "dtype")
DESC_KEYS = ("description", "desc", "comment", "label", "meaning")


@dataclass
class RawFile:
    path: Path
    sha: str
    status: str  # "new" | "changed" | "seen"
    kind: str  # "schema" | "document"


def _first(row: dict, keys) -> str:
    for k in keys:
        for actual in row:
            if actual.strip().lower() == k:
                value = row[actual]
                if value not in (None, ""):
                    return str(value).strip()
    return ""


def _manifest_path(cfg: Config) -> Path:
    return cfg.state_dir / MANIFEST


def load_manifest(cfg: Config) -> dict[str, str]:
    path = _manifest_path(cfg)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_manifest(cfg: Config, manifest: dict[str, str]) -> None:
    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    _manifest_path(cfg).write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def parse_schema_export(path: Path) -> dict[str, list[dict[str, Any]]]:
    """Pull {table: [columns]} out of a CSV/YAML/JSON export.

    Returns empty if the file does not look like a schema export, which is the
    signal that it needs a human or a skill to route it.
    """
    suffix = path.suffix.lower()
    rows: list[dict] = []

    if suffix == ".csv":
        with path.open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
    elif suffix in (".yaml", ".yml", ".json"):
        try:
            data = (
                json.loads(path.read_text(encoding="utf-8"))
                if suffix == ".json"
                else yaml.safe_load(path.read_text(encoding="utf-8"))
            )
        except Exception:
            return {}
        rows = _flatten(data)
    else:
        return {}

    tables: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        table = _first(row, TABLE_KEYS)
        column = _first(row, COLUMN_KEYS)
        if not table or not column:
            continue
        tables.setdefault(table, []).append(
            {
                "name": column,
                "type": _first(row, TYPE_KEYS),
                "description": _first(row, DESC_KEYS),
            }
        )
    return tables


def _flatten(data: Any) -> list[dict]:
    """Accept both a flat list of rows and a nested {tables: {name: {columns: ...}}}."""
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    if not isinstance(data, dict):
        return []

    for key in ("tables", "models", "datasets", "entities"):
        block = data.get(key)
        if isinstance(block, list):
            return _flatten_named(block)
        if isinstance(block, dict):
            return _flatten_named(
                [{**v, "table": k} for k, v in block.items() if isinstance(v, dict)]
            )
    return _flatten_named([data])


def _flatten_named(entries: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for entry in entries:
        table = _first(entry, TABLE_KEYS) or str(entry.get("name", ""))
        columns = entry.get("columns") or entry.get("fields") or entry.get("dimensions") or []
        if isinstance(columns, dict):
            columns = [{**v, "name": k} for k, v in columns.items() if isinstance(v, dict)]
        for col in columns:
            if isinstance(col, str):
                col = {"name": col}
            if isinstance(col, dict):
                rows.append({**col, "table": table})
    return rows


def render_columns(columns: list[dict[str, Any]]) -> str:
    lines = ["| column | type | description |", "| --- | --- | --- |"]
    for col in columns:
        name = str(col.get("name", "")).strip()
        ctype = str(col.get("type", "") or "").strip()
        desc = str(col.get("description", "") or "").strip().replace("|", "\\|")
        lines.append(f"| `{name}` | {ctype} | {desc} |")
    return "\n".join(lines)


def write_table_doc(cfg: Config, table: str, columns: list[dict], source: Path) -> tuple[Path, str]:
    """Refresh one table doc's managed region, preserving every human edit.

    A column that has vanished upstream is retired, never deleted: the reason
    someone marked it a collider outlives the column.
    """
    cfg.tables_dir.mkdir(parents=True, exist_ok=True)
    path = cfg.tables_dir / f"{table.replace('.', '_')}.md"
    rel_source = _relative(source, cfg.root)

    if path.exists():
        doc = frontmatter.load(path)
        action = "updated"
    else:
        doc = frontmatter.Doc(
            meta={"id": table, "label": table, "table": table, "kind": "table"},
            body=_new_table_body(table),
        )
        action = "created"

    incoming = {str(c.get("name", "")): c for c in columns if c.get("name")}
    existing = doc.meta.get("columns")
    existing = existing if isinstance(existing, list) else []

    merged: list[dict] = []
    seen: set[str] = set()
    for col in existing:
        if not isinstance(col, dict) or not col.get("name"):
            continue
        name = str(col["name"])
        seen.add(name)
        col = dict(col)
        if name in incoming:
            # Refresh only the upstream-owned fields; annotations are untouched.
            col["type"] = incoming[name].get("type", col.get("type", ""))
            if col.get("status") == "retired":
                del col["status"]  # it came back
        else:
            col["status"] = "retired"
        merged.append(col)

    for name, col in incoming.items():
        if name not in seen:
            merged.append({"name": name, "type": col.get("type", ""), "causal_role": "unspecified"})

    doc.meta["columns"] = merged
    doc.meta["source"] = rel_source
    doc.meta.setdefault("table", table)
    doc.body = managed.replace(
        doc.body, render_columns(columns), name="schema", source=rel_source
    )
    doc.save(path)
    return path, action


def _new_table_body(table: str) -> str:
    # The empty managed region is placed under ## Schema so that the first
    # import lands there rather than being appended below the human sections.
    return (
        f"# {table}\n\n"
        "## Schema\n\n"
        f"{managed.render('', name='schema')}\n\n"
        "## Causal annotations\n\n"
        f"{ANNOTATION_PROMPT}\n\n"
        "## Joins that work\n\n"
        "## Filters you always need\n"
    )


def _relative(path: Path, root: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(Path(root).resolve()))
    except ValueError:
        return str(path)


def scan(cfg: Config) -> list[RawFile]:
    manifest = load_manifest(cfg)
    found: list[RawFile] = []
    if not cfg.raw.exists():
        return found
    for path in sorted(cfg.raw.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        rel = _relative(path, cfg.root)
        digest = managed.sha(path.read_text(encoding="utf-8", errors="replace"))
        previous = manifest.get(rel)
        status = "new" if previous is None else ("seen" if previous == digest else "changed")
        kind = "schema" if parse_schema_export(path) else "document"
        found.append(RawFile(path=path, sha=digest, status=status, kind=kind))
    return found


def run(cfg: Config, force: bool = False) -> tuple[list[str], list[RawFile]]:
    """Import every schema export; return what was written and what needs judgement."""
    manifest = load_manifest(cfg)
    written: list[str] = []
    needs_routing: list[RawFile] = []

    for raw in scan(cfg):
        rel = _relative(raw.path, cfg.root)
        if raw.kind == "document":
            if raw.status != "seen" or force:
                needs_routing.append(raw)
            continue
        if raw.status == "seen" and not force:
            continue
        for table, columns in parse_schema_export(raw.path).items():
            path, action = write_table_doc(cfg, table, columns, raw.path)
            written.append(f"{action} {_relative(path, cfg.root)} ({len(columns)} columns)")
        manifest[rel] = raw.sha

    save_manifest(cfg, manifest)
    return written, needs_routing
