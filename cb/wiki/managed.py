"""Managed regions: re-importing must never wipe out what was added on top.

A semantic-layer export gets re-imported whenever it changes. The causal
annotations written on top of it are the most valuable thing in the wiki and
are recorded nowhere else, so ingest is only ever allowed to rewrite the bytes
between two markers:

    <!-- cb:managed source=raw/semantic_layer.yaml sha=ab12cd -->
    ...generated...
    <!-- /cb:managed -->

Everything outside is human territory and is copied through untouched.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

OPEN = "<!-- cb:managed{attrs} -->"
CLOSE = "<!-- /cb:managed -->"

_REGION = re.compile(
    r"<!--\s*cb:managed(?P<attrs>[^>]*?)-->\n?(?P<content>.*?)\n?<!--\s*/cb:managed\s*-->",
    re.DOTALL,
)
_ATTR = re.compile(r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<value>\S+)")


@dataclass
class Region:
    attrs: dict[str, str]
    content: str
    start: int
    end: int

    @property
    def name(self) -> str:
        return self.attrs.get("name", "default")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def find(text: str) -> list[Region]:
    return [
        Region(
            attrs={m.group("key"): m.group("value") for m in _ATTR.finditer(match.group("attrs"))},
            content=match.group("content"),
            start=match.start(),
            end=match.end(),
        )
        for match in _REGION.finditer(text)
    ]


def render(content: str, **attrs: str) -> str:
    rendered = "".join(f" {k}={v}" for k, v in attrs.items() if v)
    return f"{OPEN.format(attrs=rendered)}\n{content.strip()}\n{CLOSE}"


def replace(text: str, content: str, name: str = "default", **attrs: str) -> str:
    """Swap one managed region's content, leaving every other byte alone.

    If no region with this name exists, the block is appended.
    """
    block = render(content, name=name, sha=sha(content), **attrs)
    for region in find(text):
        if region.name == name:
            return text[: region.start] + block + text[region.end :]
    separator = "" if text.endswith("\n\n") or not text.strip() else "\n\n"
    return f"{text.rstrip()}{separator}\n{block}\n" if text.strip() else f"{block}\n"


def remove(text: str, name: str = "default") -> str:
    """Drop one managed region, leaving every other byte alone.

    A generated section that has nothing to say should disappear rather than
    stand there empty — an empty block in every file is noise in the wiki and
    churn in the diff.
    """
    for region in find(text):
        if region.name == name:
            cut = text[: region.start].rstrip() + "\n" + text[region.end :].lstrip("\n")
            return cut
    return text


def human_text(text: str) -> str:
    """Everything outside the managed regions — what ingest must preserve."""
    return _REGION.sub("", text)
