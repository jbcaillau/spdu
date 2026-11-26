#!/usr/bin/env python3
"""Génère le site statique (dossier docs) à partir de README.md et des notes.md.

- README.md        -> docs/index.html
- <dossier>/notes.md -> docs/<dossier>/index.html
- tous les autres fichiers (PDF, etc.) sont copiés tels quels.
"""
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

CSS = """
:root { color-scheme: light dark; }
body { max-width: 52rem; margin: 0 auto; padding: 1.5rem 1rem 4rem;
       font: 1.05rem/1.55 system-ui, -apple-system, "Segoe UI", sans-serif; }
nav { margin-bottom: 1.5rem; font-size: .95rem; }
h1, h2, h3 { line-height: 1.25; }
a { color: #1a5fb4; }
@media (prefers-color-scheme: dark) { a { color: #8ab4f8; } }
table { border-collapse: collapse; }
td, th { border: 1px solid #8884; padding: .3rem .6rem; }
code, pre { background: #8881; border-radius: 4px; }
code { padding: 0 .25em; }
pre { padding: .75rem; overflow-x: auto; }
blockquote { margin-left: 0; padding-left: 1rem; border-left: 3px solid #8886; }
"""

TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="{prefix}style.css">
</head>
<body>
{nav}
<main>
{body}
</main>
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


def render(md_path: Path, out_path: Path, is_index: bool) -> None:
    text = md_path.read_text(encoding="utf-8")
    body = markdown.markdown(
        text, extensions=["extra", "sane_lists", "toc", "nl2br"], output_format="html5"
    )
    body = rewrite_links(body)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S)
    page_title = re.sub(r"<[^>]+>", "", h1.group(1)) if h1 else SITE_TITLE
    if not is_index:
        page_title = f"{page_title} – {SITE_TITLE}"
    prefix = "../" * len(out_path.relative_to(OUT).parent.parts)
    nav = "" if is_index else f'<nav><a href="{prefix or "./"}">← {SITE_TITLE}</a></nav>'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        TEMPLATE.format(title=html.escape(page_title), prefix=prefix, nav=nav, body=body),
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
