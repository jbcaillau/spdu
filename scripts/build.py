#!/usr/bin/env python3
"""Génère le site statique (dossier docs) à partir de README.md et des notes.md.

- README.md        -> docs/index.html
- <dossier>/notes.md -> docs/<dossier>/index.html
- tous les autres fichiers (PDF, etc.) sont copiés tels quels.
"""
import datetime
import html
import re
import shutil
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs"
SKIP_DIRS = {".git", ".github", "docs", "scripts", "node_modules"}
SITE_TITLE = "SPDU"

CSS = (Path(__file__).resolve().parent / "style.css").read_text(encoding="utf-8")

TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="color-scheme" content="light dark">
<link rel="stylesheet" href="{prefix}style.css">
</head>
<body>
<header class="site-header">
<nav aria-label="Principal">
<a class="brand" href="{prefix_home}">SPDU</a>
</nav>
</header>
<main id="content">
{body}
</main>
<footer>
<span>Mis à jour le {date}</span>
</footer>
</body>
</html>
"""

LINK_MD = re.compile(r'(href=")([^"#?:]+?)((?:#[^"]*)?")')


def rewrite_links(body: str) -> str:
    """Liens relatifs vers notes.md / README.md -> liens vers les pages générées."""
    def fix(m):
        target = m.group(2)
        if target.endswith("/notes.md") or target == "notes.md":
            target = target[: -len("notes.md")] or "./"
        elif target.endswith("README.md"):
            target = target[: -len("README.md")] or "./"
        return f"{m.group(1)}{target}{m.group(3)}"
    return LINK_MD.sub(fix, body)


SEANCE_RUN = re.compile(r'(?:<p><a href="[^"]*">Séance[^<]*</a></p>\n?)+')
SEANCE_ONE = re.compile(r'<a href="[^"]*">Séance[^<]*</a>')


def join_seances(body: str) -> str:
    """Suites de paragraphes « Séance … » -> un seul paragraphe, séparés par « · »."""
    def fix(m):
        links = SEANCE_ONE.findall(m.group(0))
        return '<p class="seances">' + "&nbsp;· ".join(links) + "</p>\n"
    return SEANCE_RUN.sub(fix, body)


def render(md_path: Path, out_path: Path, is_index: bool) -> None:
    text = md_path.read_text(encoding="utf-8")
    body = markdown.markdown(
        text, extensions=["extra", "sane_lists", "toc", "nl2br"], output_format="html5"
    )
    body = join_seances(rewrite_links(body))
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S)
    page_title = re.sub(r"<[^>]+>", "", h1.group(1)) if h1 else SITE_TITLE
    if not is_index:
        page_title = f"{page_title} – {SITE_TITLE}"
    prefix = "../" * len(out_path.relative_to(OUT).parent.parts)
    home = prefix or "./"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        TEMPLATE.format(title=html.escape(page_title), prefix=prefix, prefix_home=home, body=body, date=datetime.date.today().isoformat()),
        encoding="utf-8",
    )


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    (OUT / "style.css").write_text(CSS, encoding="utf-8")
    (OUT / ".nojekyll").touch()

    pages = 0
    for src in sorted(ROOT.rglob("*")):
        rel = src.relative_to(ROOT)
        if not src.is_file() or SKIP_DIRS & set(rel.parts):
            continue
        if rel == Path("README.md"):
            render(src, OUT / "index.html", True)
            pages += 1
        elif rel.name == "notes.md":
            render(src, OUT / rel.parent / "index.html", False)
            pages += 1
        else:
            dest = OUT / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
    print(f"{pages} pages générées dans {OUT}")
    return 0 if (OUT / "index.html").exists() else 1


if __name__ == "__main__":
    sys.exit(main())
