#!/usr/bin/env python3
"""Gera o site estático da REAPR Labs a partir de content/ para dist/.

Uso:
    python build.py            # gera dist/
    python build.py --drafts   # inclui rascunhos (draft: true), para prévia local
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
DIST = ROOT / "dist"

FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.S)
SLUG_OK = re.compile(r"^[a-z0-9][a-z0-9-]*$")

# Textos de /writing/: post-mortems e notas.
WRITING_KINDS = {"PM": "Post-mortem", "NOTE": "Note"}
# Estados de um caso em /work/.
WORK_STATUS = ("planned", "in progress", "done")


class BuildError(Exception):
    pass


@dataclass
class Entry:
    section: str  # "work" | "writing" | "pages"
    slug: str
    meta: dict
    body_html: str
    toc_html: str = ""
    url: str = ""

    @property
    def date(self) -> dt.date | None:
        d = self.meta.get("date")
        if isinstance(d, dt.datetime):
            return d.date()
        if isinstance(d, dt.date):
            return d
        if isinstance(d, str) and d:
            return dt.date.fromisoformat(d)
        return None


def as_list(value) -> list[str]:
    """Aceita lista YAML ou texto separado por vírgula."""
    if not value:
        return []
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return [str(v) for v in value]


def read_entry(path: Path, section: str) -> Entry:
    text = path.read_text(encoding="utf-8")
    m = FRONT_MATTER.match(text)
    if not m:
        raise BuildError(f"{path}: falta o cabeçalho '---' com os metadados")
    meta = yaml.safe_load(m.group(1)) or {}
    if not isinstance(meta, dict):
        raise BuildError(f"{path}: cabeçalho inválido")
    slug = path.stem
    if not SLUG_OK.match(slug):
        raise BuildError(f"{path}: nome de arquivo inválido. Use minúsculas, números e hífen")
    if not meta.get("title"):
        raise BuildError(f"{path}: 'title' é obrigatório")

    md = markdown.Markdown(
        extensions=["fenced_code", "tables", "footnotes", "attr_list", "def_list", "toc", "sane_lists"],
        extension_configs={"toc": {"permalink": False, "toc_depth": "2-3"}},
        output_format="html",
    )
    body = md.convert(m.group(2))
    entry = Entry(section=section, slug=slug, meta=meta, body_html=body, toc_html=md.toc)

    if section in ("work", "writing") and entry.date is None:
        raise BuildError(f"{path}: 'date' é obrigatório (AAAA-MM-DD)")

    if section == "work":
        status = str(meta.get("status", "")).lower()
        if status not in WORK_STATUS:
            raise BuildError(f"{path}: 'status' deve ser um de: {', '.join(WORK_STATUS)}")
        meta["status"] = status
        if not isinstance(meta.get("case"), int):
            raise BuildError(f"{path}: 'case' deve ser um número inteiro (ex.: 1)")
        for key in ("problem", "approach"):
            if not meta.get(key):
                raise BuildError(f"{path}: '{key}' é obrigatório num caso")
        # Resultado só entra quando existir: nada de número inventado.
        meta.setdefault("result", "")
        meta["stack"] = as_list(meta.get("stack"))
        meta.setdefault("featured", True)

    if section == "writing":
        kind = str(meta.get("kind", "")).upper()
        if kind not in WRITING_KINDS:
            raise BuildError(f"{path}: 'kind' deve ser um de: {', '.join(WRITING_KINDS)}")
        meta["kind"] = kind
        meta["kind_label"] = WRITING_KINDS[kind]

    return entry


def load_section(section: str, include_drafts: bool) -> list[Entry]:
    folder = CONTENT / section
    if not folder.exists():
        return []
    entries = []
    for path in sorted(folder.glob("*.md")):
        if path.name.startswith("_"):  # modelos e arquivos ignorados
            continue
        e = read_entry(path, section)
        if e.meta.get("draft") and not include_drafts:
            continue
        entries.append(e)
    return entries


def deploy_info() -> dict | None:
    """Commit publicado, lido das variáveis que o GitHub Actions define. Local: None."""
    sha = os.environ.get("GITHUB_SHA", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    if not sha or not repo:
        return None
    return {"sha": sha[:7], "url": f"{server}/{repo}/commit/{sha}"}


def build(include_drafts: bool = False) -> int:
    cfg = yaml.safe_load((ROOT / "site.yaml").read_text(encoding="utf-8")) or {}
    base = str(cfg.get("base_path") or "").rstrip("/")
    cfg["base_path"] = base

    work = load_section("work", include_drafts)
    work.sort(key=lambda e: e.meta["case"])
    writing = load_section("writing", include_drafts)
    writing.sort(key=lambda e: e.date or dt.date.min, reverse=True)
    pages = load_section("pages", include_drafts)

    cases = [e.meta["case"] for e in work]
    dupes = {c for c in cases if cases.count(c) > 1}
    if dupes:
        raise BuildError(f"números de caso repetidos: {', '.join(map(str, sorted(dupes)))}")

    for e in work:
        e.url = f"{base}/work/{e.slug}/"
    for e in writing:
        e.url = f"{base}/writing/{e.slug}/"
    for e in pages:
        e.url = f"{base}/{e.slug}/"

    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["isodate"] = lambda d: d.isoformat() if d else ""

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    shutil.copytree(STATIC, DIST / "static")

    common = {
        "site": cfg,
        "base": base,
        "year": dt.date.today().year,
        "build_date": dt.date.today().isoformat(),
        "deploy": deploy_info(),
        "has_writing": bool(writing),
    }

    def render(template: str, out: str, **ctx) -> None:
        target = DIST / out
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(env.get_template(template).render(**common, **ctx), encoding="utf-8")

    about = next((p for p in pages if p.slug == "about"), None)

    render("home.html", "index.html", nav="home",
           featured=[e for e in work if e.meta["featured"]], writing=writing[:5])
    render("list.html", "work/index.html", nav="work", heading="Work", kind="work",
           intro="Projects run like production: each one states the problem, the approach and, when it exists, the measured result.",
           entries=work, empty="The first case is in progress.")
    render("list.html", "writing/index.html", nav="writing", heading="Post-mortems and notes", kind="writing",
           intro="Blameless post-mortems from lab incidents and short notes from the work.",
           entries=writing, empty="Nothing published yet. The first post-mortem will come from running this site.")
    for e in work:
        render("entry.html", f"work/{e.slug}/index.html", e=e, nav="work")
    for e in writing:
        render("entry.html", f"writing/{e.slug}/index.html", e=e, nav="writing")
    for e in pages:
        render("page.html", f"{e.slug}/index.html", e=e, nav=e.slug)
    render("404.html", "404.html", nav="")
    render("feed.xml", "feed.xml", writing=writing)

    (DIST / ".nojekyll").write_text("", encoding="utf-8")
    # Domínio próprio: o CNAME da raiz do projeto vai para a raiz do site.
    if (ROOT / "CNAME").exists():
        shutil.copy(ROOT / "CNAME", DIST / "CNAME")

    if about is None:
        print("aviso: content/pages/about.md não existe", file=sys.stderr)
    print(f"ok: {len(work)} caso(s), {len(writing)} texto(s), {len(pages)} página(s) -> {DIST}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--drafts", action="store_true", help="inclui rascunhos (draft: true)")
    args = ap.parse_args()
    try:
        return build(include_drafts=args.drafts)
    except BuildError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
