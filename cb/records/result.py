"""Bringing a notebook back.

A notebook run outside Claude Code and carried back is a completed piece of
work, not an error. It is the normal path — the data lives in the analyst's
environment, not here — so it gets a first-class command rather than being
handled as a fallback.

Accepts an executed .ipynb (outputs extracted to readable markdown) or any
text/markdown/csv file pasted in.
"""

from __future__ import annotations

import datetime as _dt
import shutil
from pathlib import Path

MAX_OUTPUT_CHARS = 4000


def _text_of(output) -> str:
    """Pull readable text out of one nbformat output object."""
    kind = output.get("output_type")
    if kind == "stream":
        return "".join(output.get("text", ""))
    if kind in ("execute_result", "display_data"):
        data = output.get("data", {})
        if "text/plain" in data:
            return "".join(data["text/plain"])
        if "image/png" in data:
            return "[image output — open the notebook to view]"
        return f"[{', '.join(data)} output]"
    if kind == "error":
        # Failed notebooks are the useful ones. Keep the traceback.
        return "\n".join(output.get("traceback", [])) or output.get("evalue", "")
    return ""


def notebook_to_markdown(path: Path) -> str:
    import nbformat

    nb = nbformat.read(Path(path), as_version=4)
    lines = [f"# Result — {Path(path).name}", ""]
    failed = False

    for i, cell in enumerate(nb.cells, start=1):
        source = "".join(cell.get("source", "")).strip()
        if not source:
            continue
        if cell.get("cell_type") == "markdown":
            lines += [source, ""]
            continue
        if cell.get("cell_type") != "code":
            continue

        outputs = cell.get("outputs", [])
        rendered = "\n".join(t for t in (_text_of(o) for o in outputs) if t).strip()
        if any(o.get("output_type") == "error" for o in outputs):
            failed = True

        lines += [f"## Cell {i}", "", "```python", source, "```", ""]
        if rendered:
            if len(rendered) > MAX_OUTPUT_CHARS:
                rendered = rendered[:MAX_OUTPUT_CHARS] + "\n… [truncated]"
            lines += ["**Output**", "", "```", rendered, "```", ""]

    if failed:
        lines.insert(2, "> This notebook raised an error. Recorded deliberately — "
                        "the runs that fail are the ones worth keeping.\n")
    return "\n".join(lines)


def add(question, source: Path, note: str = "") -> Path:
    """Attach an executed notebook or output file to a question record."""
    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(f"no such file: {source}")

    question.results_dir.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")

    if source.suffix == ".ipynb":
        # Keep the original alongside the readable rendering.
        shutil.copy2(source, question.results_dir / f"{stamp}-{source.name}")
        target = question.results_dir / f"{stamp}-{source.stem}.md"
        target.write_text(notebook_to_markdown(source), encoding="utf-8")
    else:
        target = question.results_dir / f"{stamp}-{source.name}"
        shutil.copy2(source, target)

    question.stamp("result", note or f"brought back {source.name}")
    return target
