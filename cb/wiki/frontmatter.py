"""Read and write markdown files with YAML frontmatter.

The body is always preserved verbatim. Frontmatter is re-serialised canonically
so that a file cb has written round-trips byte-identically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DELIM = "---"

# Frontmatter keys are emitted in this order, then anything else alphabetically.
# Stable ordering is what makes `git diff` on the wiki readable.
KEY_ORDER = [
    "id",
    "label",
    "kind",
    "observed",
    "table",
    "column",
    "measured",
    "causal_role",
    "graphs",
    "status",
    "source",
    "confirmed_by",
    "confirmed_at",
]


class FrontmatterError(ValueError):
    """A markdown file's frontmatter is missing or malformed."""


@dataclass
class Doc:
    """A markdown document: a frontmatter mapping plus a verbatim body."""

    meta: dict[str, Any] = field(default_factory=dict)
    body: str = ""
    path: Path | None = None

    def dump(self) -> str:
        return dumps(self.meta, self.body)

    def save(self, path: Path | None = None) -> Path:
        target = Path(path or self.path)  # type: ignore[arg-type]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.dump(), encoding="utf-8")
        return target


def _order_keys(meta: dict[str, Any]) -> dict[str, Any]:
    known = [k for k in KEY_ORDER if k in meta]
    rest = sorted(k for k in meta if k not in KEY_ORDER)
    return {k: meta[k] for k in known + rest}


def dumps(meta: dict[str, Any], body: str) -> str:
    """Serialise to canonical `---\\nyaml\\n---\\n\\nbody` form."""
    text = yaml.safe_dump(
        _order_keys(meta),
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).rstrip("\n")
    body = body.strip("\n")
    return f"{DELIM}\n{text}\n{DELIM}\n\n{body}\n" if body else f"{DELIM}\n{text}\n{DELIM}\n"


def loads(text: str, path: Path | None = None) -> Doc:
    if not text.startswith(DELIM):
        raise FrontmatterError(
            f"{path or '<string>'}: file does not start with a '---' frontmatter block"
        )
    # Split on the closing delimiter only, so '---' inside the body is safe.
    rest = text[len(DELIM) :].lstrip("\n")
    end = rest.find(f"\n{DELIM}")
    if end == -1:
        raise FrontmatterError(f"{path or '<string>'}: frontmatter block is never closed")
    raw_meta, body = rest[:end], rest[end + len(DELIM) + 1 :]
    try:
        meta = yaml.safe_load(raw_meta) or {}
    except yaml.YAMLError as exc:
        raise FrontmatterError(f"{path or '<string>'}: invalid YAML frontmatter: {exc}") from exc
    if not isinstance(meta, dict):
        raise FrontmatterError(
            f"{path or '<string>'}: frontmatter must be a mapping, got {type(meta).__name__}"
        )
    return Doc(meta=meta, body=body.strip("\n"), path=path)


def load(path: Path) -> Doc:
    path = Path(path)
    return loads(path.read_text(encoding="utf-8"), path=path)
