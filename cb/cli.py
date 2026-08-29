"""The `cb` command line.

`cb` is deterministic Python. It does not call an LLM and holds no API key —
the judgement lives in `skills/`, and Claude Code drives these commands through
the slash commands in `.claude/commands/cb/`. So `cb ask` allocates the question
and assembles the context; it does not conduct the interview.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

from . import context as context_mod
from . import doctor as doctor_mod
from . import ingest as ingest_mod
from . import templates as templates_mod
from .config import Config, load as load_config
from .identify import engine
from .index import build as index_build
from .index import queries
from .notebook import scaffold
from .records import question as qmod
from .records import result as result_mod
from .wiki import backlinks as backlinks_mod
from .wiki import graph as wikigraph
from .wiki import methods as methods_mod

app = typer.Typer(add_completion=False, help=__doc__, no_args_is_help=True)
graph_app = typer.Typer(help="Inspect the causal graph.", no_args_is_help=True)
notebook_app = typer.Typer(help="Notebook scaffolding.", no_args_is_help=True)
result_app = typer.Typer(help="Bring an executed notebook back.", no_args_is_help=True)
app.add_typer(graph_app, name="graph")
app.add_typer(notebook_app, name="notebook")
app.add_typer(result_app, name="result")


def echo(text: str = "") -> None:
    typer.echo(text)


def fail(message: str) -> None:
    typer.secho(f"error: {message}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1)


def cfg() -> Config:
    try:
        return load_config()
    except FileNotFoundError as exc:
        fail(str(exc))
        raise  # unreachable; keeps type checkers happy


# -- init ---------------------------------------------------------------------


@app.command()
def init(
    path: Path = typer.Argument(Path("."), help="Where to create the project."),
    force: bool = typer.Option(False, "--force", help="Replace skills you have edited."),
) -> None:
    """Create the wiki skeleton, the skills and the slash commands."""
    root = Path(path).resolve()
    c = Config(root=root)
    for directory in c.dirs():
        directory.mkdir(parents=True, exist_ok=True)
    gitignore = root / ".gitignore"
    line = ".cb/\n"
    if not gitignore.exists() or line not in gitignore.read_text(encoding="utf-8"):
        with gitignore.open("a", encoding="utf-8") as fh:
            fh.write(f"\n# cb: derived index, rebuilt by `cb index`\n{line}")

    written = templates_mod.materialise(root, force=force)
    echo(f"initialised cb project at {root}")
    _report_templates(written)
    echo()
    echo("CLAUDE.md is the standing context Claude Code reads on every session; "
         "skills/ is the judgement layer. Both are yours to edit.")
    echo("Next: drop material into raw/ and run /cb:ingest in Claude Code.")


@app.command()
def sync(
    force: bool = typer.Option(False, "--force", help="Replace skills you have edited."),
) -> None:
    """Refresh the shipped skills and slash commands after upgrading cb."""
    c = cfg()
    _report_templates(
        templates_mod.materialise(c.root, force=force, groups=templates_mod.SYNCED)
    )
    # Never with `force`: a project's CLAUDE.md is its own, and sync must not be
    # able to take it back. But a *missing* one is not an edit, it is the
    # always-on context absent — and the whole judgement layer assumes it is there.
    restored = [
        w
        for w in templates_mod.materialise(c.root, groups=[templates_mod.PROJECT])
        if w.action == "created"
    ]
    for w in restored:
        echo(f"  {w}")
    if restored:
        echo()
        echo("CLAUDE.md was missing — written back. It is the standing context that "
             "tells Claude this is causal work; without it the skills are half the tool.")


def _report_templates(written: list) -> None:
    kept = [w for w in written if w.action == "kept"]
    for w in written:
        if w.action != "unchanged":
            echo(f"  {w}")
    if kept:
        echo()
        echo(
            f"{len(kept)} file(s) you had edited were left alone. The skills are meant "
            f"to be changed — pass --force only if you want the shipped versions back."
        )


# -- stage one: collecting ----------------------------------------------------


@app.command()
def ingest(
    force: bool = typer.Option(False, "--force", help="Re-import files already seen."),
    scan_only: bool = typer.Option(False, "--scan", help="List raw files, change nothing."),
) -> None:
    """Read raw/, refresh table docs, and list what still needs judgement."""
    c = cfg()

    if scan_only:
        found = ingest_mod.scan(c)
        if not found:
            echo(f"nothing in {c.raw}")
            return
        for raw in found:
            echo(f"{raw.status:8s} {raw.kind:9s} {raw.path.relative_to(c.root)}")
        return

    written, needs_routing = ingest_mod.run(c, force=force)

    for line in written:
        echo(line)
    if not written:
        echo("no schema exports to import")

    if needs_routing:
        echo()
        echo("These need routing — read each and write it into the wiki")
        echo("(follow skills/routing.md; record where every fact came from):")
        for raw in needs_routing:
            echo(f"  [{raw.status}] {raw.path.relative_to(c.root)}")
        echo()
        echo("Ingest writes no causal edges by design. The graph is drawn in the interview.")


# -- stage two: a question arrives --------------------------------------------


@app.command()
def ask(
    question: str = typer.Argument(..., help="The question, as the business asked it."),
    asked_by: str = typer.Option("", "--asked-by"),
    graph: str = typer.Option(None, "--graph", help="Named graph this belongs to."),
) -> None:
    """Open a question record. The interview happens in Claude Code, not here."""
    c = cfg()
    already = context_mod.similar_questions(c, question)
    q = qmod.create(c.questions, question, asked_by=asked_by, graph=graph)
    echo(f"{q.id}  {q.dir.relative_to(c.root)}")  # type: ignore[union-attr]

    # Cheap, and it catches the failure a wiki exists to prevent: the same
    # question answered twice, months apart, by two different people.
    if already:
        echo()
        echo("This looks close to something already asked:")
        for prior, overlap in already:
            line = f"  {prior.id} [{prior.status.value}] {prior.question}"
            if prior.verdict:
                line += f" — {prior.verdict}"
            echo(line)
            if prior.finding:
                echo(f"      {prior.finding}")
        echo("  Read it first — it may already answer this, or say why it could not.")
    echo()
    echo("Next: read the wiki and interview the analyst (skills/interview.md).")
    echo(f"Save the interview to {q.interview_path.relative_to(c.root)}, then run:")
    echo(f"  cb identify {q.id}")


@app.command()
def context(
    qid: str = typer.Argument(..., help="Question id."),
    limit: int = typer.Option(12, "--limit", help="How many prior questions to show."),
    all_: bool = typer.Option(False, "--all", help="Every prior question, unranked cap lifted."),
) -> None:
    """Print the wiki context pack for a question, so Claude need not grep blind."""
    c = cfg()
    try:
        q = qmod.find(c.questions, qid)
    except FileNotFoundError as exc:
        fail(str(exc))
        return

    echo(f"# {q.id} — {q.question}")
    echo(f"status: {q.status.value}")
    if q.treatment or q.outcome:
        echo(f"treatment: {', '.join(q.treatment)}    outcome: {', '.join(q.outcome)}")
    echo()

    wiki = None
    if c.graph_dir.exists():
        wiki = wikigraph.load(c.graph_dir)
        echo(f"## Graphs ({len(wiki.nodes)} nodes)")
        for name in wiki.graph_names():
            members = sorted(wiki.view(name))
            echo(f"- **{name}**: {', '.join(members)}")
        unobserved = sorted(wiki.unobserved())
        if unobserved:
            echo(f"- unobserved: {', '.join(unobserved)}")
        echo()

    for label, directory in (
        ("Tables", c.tables_dir),
        ("Rules (these decide who gets treated)", c.rules_dir),
        ("Process", c.process_dir),
        ("Methods used here", c.methods_dir),
        ("Experiments", c.experiments_dir),
        ("Traps", c.traps_dir),
    ):
        if not directory.exists():
            continue
        files = sorted(directory.rglob("*.md"))
        if files:
            echo(f"## {label}")
            for f in files:
                echo(f"- {f.relative_to(c.root)}")
            echo()

    _echo_priors(c, q, wiki, limit=None if all_ else limit)
    echo("Search past interviews with: cb find \"<terms>\"")


def _echo_priors(c: Config, q, wiki, limit: int | None) -> None:
    """Prior questions, most relevant first.

    An unranked dump was fine at twenty questions and useless at three hundred:
    the ones that bear on this question have to be at the top, or the pack stops
    being read.
    """
    ranked = context_mod.rank_priors(c, q, wiki)
    if not ranked:
        return
    shown = ranked if limit is None else ranked[:limit]
    echo(f"## Prior questions ({len(shown)} of {len(ranked)}, most relevant first)")
    for r in shown:
        p = r.question
        line = f"- {p.id} [{p.status.value}] {p.question}"
        if p.verdict:
            line += f" — {p.verdict}"
        echo(line)
        if r.reason:
            echo(f"    ↳ {r.reason}")
    if len(ranked) > len(shown):
        rest = len(ranked) - len(shown)
        echo(f"- …and {rest} more, less related. `cb context {q.id} --all`, "
             f"or search them with `cb find`.")
    echo()


# -- stage three-and-a-half: identification -----------------------------------


@app.command()
def identify(
    qid: str = typer.Argument(..., help="Question id, or 'adhoc' with --treatment/--outcome."),
    treatment: list[str] = typer.Option(None, "--treatment", help="Ad-hoc override."),
    outcome: list[str] = typer.Option(None, "--outcome", help="Ad-hoc override."),
    graph: str = typer.Option(None, "--graph"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Decide whether the effect can be recovered from what is observed.

    Refuses rather than caveats, and always names a design that would work.
    """
    c = cfg()
    q = None
    if qid != "adhoc":
        try:
            q = qmod.find(c.questions, qid)
        except FileNotFoundError as exc:
            fail(str(exc))
            return

    t = list(treatment or (q.treatment if q else []))
    y = list(outcome or (q.outcome if q else []))
    if not t or not y:
        fail(
            "no treatment/outcome on the question record. These come out of the interview — "
            "write them into question.md, or pass --treatment/--outcome for an ad-hoc check."
        )

    wiki = wikigraph.load(c.graph_dir)
    try:
        report = engine.identify(
            wiki,
            t,
            y,
            question_id=q.id if q else "adhoc",
            graph_name=graph or (q.graph if q else None),
        )
    except engine.GraphError as exc:
        fail(str(exc))
        return

    if as_json:
        echo(json.dumps(report.model_dump(mode="json"), indent=2))
    else:
        echo(report.to_markdown())

    if q is not None:
        report.save(q.identification_path)
        q.identification_path.with_suffix(".md").write_text(
            report.to_markdown(), encoding="utf-8"
        )
        q.verdict = report.verdict.value
        q.status = qmod.Status.IDENTIFIED if report.identified else qmod.Status.REFUSED
        q.treatment, q.outcome = t, y
        q.save()
        q.stamp("identify", report.verdict.value)

    if not report.identified:
        raise typer.Exit(code=2)


# -- stage four: the notebook -------------------------------------------------


@notebook_app.command("new")
def notebook_new(
    qid: str = typer.Argument(...),
    name: str = typer.Option(None, "--name"),
) -> None:
    """Scaffold a notebook carrying the identification verdict."""
    c = cfg()
    try:
        q = qmod.find(c.questions, qid)
    except FileNotFoundError as exc:
        fail(str(exc))
        return

    report = None
    if q.identification_path.exists():
        from .identify.report import Report

        report = Report(**json.loads(q.identification_path.read_text(encoding="utf-8")))

    path = scaffold.build(q, report=report, name=name)
    if q.status in (qmod.Status.IDENTIFIED, qmod.Status.REFUSED):
        q.status = qmod.Status.NOTEBOOK
        q.save()
    echo(f"wrote {path.relative_to(c.root)}")
    echo("Run it where the data is, then: cb result add "
         f"{q.id} <executed notebook>")


# -- stage five: coming back --------------------------------------------------


@result_app.command("add")
def result_add(
    qid: str = typer.Argument(...),
    path: Path = typer.Argument(..., help="Executed .ipynb, or any output file."),
    note: str = typer.Option("", "--note"),
) -> None:
    """Attach an executed notebook. This is the normal path, not a fallback."""
    c = cfg()
    try:
        q = qmod.find(c.questions, qid)
        target = result_mod.add(q, path, note=note)
    except FileNotFoundError as exc:
        fail(str(exc))
        return
    q.status = qmod.Status.ANALYSING
    q.save()
    echo(f"recorded {target.relative_to(c.root)}")
    echo("Read it, then refine, re-run, or conclude.")


# -- the index ----------------------------------------------------------------


@app.command("index")
def index_cmd(
    backlinks: bool = typer.Option(
        True, "--backlinks/--no-backlinks",
        help="Also refresh the 'Questions asked here' block on each node file.",
    ),
) -> None:
    """Rebuild the DuckDB index from the wiki. Derived, disposable, never authoritative."""
    c = cfg()
    path = index_build.build(c)
    counts = queries.summary(c)
    echo(f"rebuilt {path.relative_to(c.root)}")
    echo("  " + "  ".join(f"{k}={v}" for k, v in counts.items()))

    # The database is disposable; this is not. It is a generated region inside a
    # file a human owns, which is why it goes through `managed` and why it is
    # written here — so the backlinks can never drift from the records.
    if backlinks and c.graph_dir.exists():
        changed = backlinks_mod.update(c, wikigraph.load(c.graph_dir))
        if changed:
            echo(f"  backlinks refreshed on {len(changed)} node file(s)")


@app.command()
def gaps(
    kind: list[str] = typer.Option(None, "--kind", help="Restrict to one gap kind."),
) -> None:
    """What haven't we looked at?"""
    c = cfg()
    try:
        found = queries.gaps(c, kinds=list(kind) if kind else None)
    except FileNotFoundError as exc:
        fail(str(exc))
        return
    if not found:
        echo("no gaps found")
        return
    current = None
    for gap in found:
        if gap.kind != current:
            current = gap.kind
            echo()
            echo(f"## {current}")
        echo(f"  {gap.subject:40s} {gap.detail}")


@app.command()
def find(
    query: str = typer.Argument(..., help="Search interviews, questions, tables, traps."),
    limit: int = typer.Option(20, "--limit"),
) -> None:
    """Search what has already been learned."""
    c = cfg()
    try:
        rows = queries.find(c, query, limit=limit)
    except FileNotFoundError as exc:
        fail(str(exc))
        return
    if not rows:
        echo("no matches")
        return
    for kind, ref, title, path in rows:
        echo(f"{kind:11s} {ref:14s} {title[:44]:44s} {path}")


@app.command()
def sql(statement: str = typer.Argument(..., help="Read-only SQL over the index.")) -> None:
    """Query the index directly."""
    c = cfg()
    try:
        cols, rows = queries.query(c, statement)
    except FileNotFoundError as exc:
        fail(str(exc))
        return
    echo(" | ".join(cols))
    for row in rows:
        echo(" | ".join("" if v is None else str(v) for v in row))


# -- validation ---------------------------------------------------------------


@app.command()
def methods() -> None:
    """What this company has estimated with before, and how often.

    The textbook is already in the model. This is the local record: which of
    them survived contact with this business, and which were tried with nothing
    written down about how they had to be bent.
    """
    c = cfg()
    notes = methods_mod.load(c)
    questions = [q for q in qmod.iter_questions(c.questions) if q.method]

    used: dict[str, list] = {}
    unwritten: dict[str, list] = {}
    for q in questions:
        note = methods_mod.match(notes, q.method or "")
        if note:
            used.setdefault(note.id, []).append(q)
        else:
            unwritten.setdefault(q.method or "", []).append(q)

    if notes:
        echo("## Written up")
        for note in notes:
            ids = ", ".join(q.id for q in sorted(used.get(note.id, []), key=lambda q: q.id))
            echo(f"  {note.id:34s} {len(used.get(note.id, [])):2d}  {ids or '—'}")
    else:
        echo(f"nothing in {c.methods_dir.relative_to(c.root)} yet")

    if unwritten:
        echo()
        echo("## Used but never written up")
        for method, qs in sorted(unwritten.items()):
            echo(f"  {method:34s} {len(qs):2d}  {', '.join(q.id for q in qs)}")
        echo()
        echo("Each of these was tailored to this business somehow. Write that down in "
             f"{c.methods_dir.relative_to(c.root)}/ — skills/methods.md has the shape.")


@app.command()
def doctor(
    strict: bool = typer.Option(False, "--strict", help="Exit non-zero on warnings too."),
) -> None:
    """Check the wiki for the errors that silently corrupt verdicts."""
    c = cfg()
    findings = doctor_mod.check(c)
    echo(doctor_mod.report(findings))
    errors = [f for f in findings if f.level == "error"]
    if errors or (strict and findings):
        raise typer.Exit(code=1)


@graph_app.command("list")
def graph_list() -> None:
    """Named graphs and their nodes."""
    c = cfg()
    wiki = wikigraph.load(c.graph_dir)
    names = wiki.graph_names()
    if not names:
        echo("no named graphs (add a `graphs:` list to node frontmatter)")
    for name in names:
        members = sorted(wiki.view(name))
        latent = [m for m in members if not wiki.nodes[m].observed]
        echo(f"{name}  ({len(members)} nodes"
             + (f", unobserved: {', '.join(latent)}" if latent else "") + ")")
        for member in members:
            echo(f"    {member}")


@graph_app.command("show")
def graph_show(
    name: str = typer.Argument(None, help="Named graph; omit for everything."),
    arithmetic: bool = typer.Option(False, "--arithmetic", help="Show identities instead."),
) -> None:
    """Print the edges, as a check that the files parse the way you read them."""
    c = cfg()
    wiki = wikigraph.load(c.graph_dir)
    g = wiki.arithmetic() if arithmetic else wiki.causal()
    if name:
        g = g.subgraph(wiki.view(name)).copy()
    if not g.edges:
        echo("no edges")
        return
    for s, t, data in sorted(g.edges(data=True)):
        mark = "" if data.get("confirmed_by", "") != "claude-proposed" else "  [unconfirmed]"
        arrow = "=" if arithmetic else "->"
        echo(f"{s} {arrow} {t}{mark}")
        if data.get("reason"):
            echo(f"    {data['reason']}")


@app.command()
def status(
    status_: list[str] = typer.Option(
        None, "--status", help="Only these statuses. Repeatable."
    ),
    asked_by: str = typer.Option("", "--asked-by", help="Only what this person asked."),
    since: str = typer.Option("", "--since", help="Only touched on or after this ISO date."),
    all_: bool = typer.Option(False, "--all", help="Include concluded and abandoned too."),
) -> None:
    """Where every open question stands.

    Closed questions are counted rather than listed: past a hundred of them the
    list is an archive, and the archive is what `cb find` is for.
    """
    c = cfg()
    rows = list(qmod.iter_questions(c.questions))
    if not rows:
        echo("no questions yet — start with: cb ask \"<what they asked>\"")
        return

    wanted = {s.lower() for s in (status_ or [])}
    closed = 0
    shown = []
    for q in rows:
        if wanted:
            if q.status.value not in wanted:
                continue
        elif not all_ and q.status in qmod.TERMINAL:
            closed += 1
            continue
        if asked_by and q.asked_by != asked_by:
            continue
        if since and q.last_activity[:10] < since:
            continue
        shown.append(q)

    shown.sort(key=lambda q: q.last_activity, reverse=True)
    for q in shown:
        line = f"{q.id}  {q.last_activity[:10]}  {q.status.value:13s} {q.question}"
        if q.verdict:
            line += f"  [{q.verdict}]"
        echo(line)

    if not shown:
        echo("nothing matches")
    if closed:
        echo()
        echo(f"{closed} concluded or abandoned, not shown. `cb status --all` for everything.")


def main() -> None:
    try:
        app()
    except BrokenPipeError:
        sys.exit(0)


if __name__ == "__main__":
    main()
