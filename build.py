#!/usr/bin/env python3
"""
Static blog builder.

Usage:
  python3 build.py  # wipe dist/ and rebuild the site
"""

import argparse
import json
import re
import shutil
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

# ── Config ────────────────────────────────────────────────────────────────────

SITE_NAME = "My Blog"
SITE_DESCRIPTION = "A personal blog."

POSTS_DIR = Path("posts")
TEMPLATES_DIR = Path("templates")
STATIC_DIR = Path("static")
IMAGES_DIR = Path("images")
OUTPUT_DIR = Path("dist")
LINKS_FILE = Path("data/links.json")

# ── Helpers ───────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text


def parse_post(path: Path):
    """Parse a post file, returning a dict or None if it should be skipped."""
    raw = path.read_text(encoding="utf-8")

    # Extract YAML front matter between --- delimiters
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.DOTALL)
    if not match:
        print(f"  WARNING: No front matter found in {path.name}, skipping.")
        return None

    meta_raw, content = match.group(1), match.group(2).strip()

    try:
        meta = yaml.safe_load(meta_raw) or {}
    except yaml.YAMLError as e:
        print(f"  WARNING: Bad YAML in {path.name}: {e}, skipping.")
        return None

    # Skip drafts
    if meta.get("draft", False):
        return None

    # Required fields
    if "title" not in meta:
        print(f"  WARNING: No title in {path.name}, skipping.")
        return None
    if "date" not in meta:
        print(f"  WARNING: No date in {path.name}, skipping.")
        return None

    # Normalise date to a date object
    raw_date = meta["date"]
    if isinstance(raw_date, datetime):
        post_date = raw_date.date()
    elif isinstance(raw_date, date):
        post_date = raw_date
    else:
        try:
            post_date = datetime.strptime(str(raw_date), "%Y-%m-%d").date()
        except ValueError:
            print(f"  WARNING: Bad date format in {path.name} (use YYYY-MM-DD), skipping.")
            return None

    # Normalise categories to a list
    categories = meta.get("categories", [])
    if isinstance(categories, str):
        categories = [categories]
    categories = [c.strip() for c in categories if c]

    # Normalise type to a string or None
    post_type = meta.get("type", None)
    if post_type:
        post_type = str(post_type).strip() or None

    # Derive slug from filename (strip .html extension)
    slug = meta.get("slug") or slugify(path.stem)

    return {
        "title": meta["title"],
        "date": post_date,
        "categories": categories,
        "type": post_type,
        "description": meta.get("description", ""),
        "author": meta.get("author", ""),
        "slug": slug,
        "content": content,
        "source_path": path,
    }


# ── Build ─────────────────────────────────────────────────────────────────────

def build() -> None:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
        print(f"Cleaned {OUTPUT_DIR}/")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Jinja2 env
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,          # content is trusted HTML
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["slugify"] = slugify
    env.filters["tojson"] = json.dumps

    # ── Load links ─────────────────────────────────────────────────────────────
    links = []
    if LINKS_FILE.exists():
        links = json.loads(LINKS_FILE.read_text(encoding="utf-8"))
        print(f"Loaded {len(links)} link(s) from {LINKS_FILE}")

    # ── Collect posts ──────────────────────────────────────────────────────────
    print("Reading posts…")
    posts = []
    for path in sorted(POSTS_DIR.glob("*.html")):
        post = parse_post(path)
        if post:
            posts.append(post)
            print(f"  ✓ {path.name}")

    # Sort newest first
    posts.sort(key=lambda p: p["date"], reverse=True)

    total_posts = len(posts)
    current_year = datetime.now().year

    # Build category index (used both for nav dropdown and category pages)
    by_category: dict[str, list] = defaultdict(list)
    for post in posts:
        for cat in post["categories"]:
            by_category[cat].append(post)

    all_categories = [
        {"name": cat, "slug": slugify(cat)}
        for cat in sorted(by_category)
    ]

    # Build type index
    by_type: dict[str, list] = defaultdict(list)
    for post in posts:
        if post["type"]:
            by_type[post["type"]].append(post)

    all_types = [
        {"name": t, "slug": slugify(t)}
        for t in sorted(by_type)
    ]

    def base_ctx(root_path: str = "") -> dict:
        return {
            "site_name": SITE_NAME,
            "site_description": SITE_DESCRIPTION,
            "root_path": root_path,
            "post_count": total_posts,
            "current_year": current_year,
            "all_categories": all_categories,
            "all_types": all_types,
            "has_links": bool(links),
        }

    # ── Render index ───────────────────────────────────────────────────────────
    print("\nRendering index…")
    tmpl = env.get_template("index.html")
    (OUTPUT_DIR / "index.html").write_text(
        tmpl.render(**base_ctx(), posts=posts),
        encoding="utf-8",
    )
    print("  ✓ dist/index.html")

    # ── Render posts ───────────────────────────────────────────────────────────
    print("\nRendering posts…")
    post_tmpl = env.get_template("post.html")
    posts_out = OUTPUT_DIR / "posts"
    posts_out.mkdir(exist_ok=True)

    for post in posts:
        post_dir = posts_out / post["slug"]
        post_dir.mkdir(exist_ok=True)
        out_path = post_dir / "index.html"
        out_path.write_text(
            post_tmpl.render(**base_ctx(root_path="../../"), post=post),
            encoding="utf-8",
        )
        print(f"  ✓ dist/posts/{post['slug']}/index.html")

    # ── Render category pages ──────────────────────────────────────────────────
    print("\nRendering categories…")
    cat_tmpl = env.get_template("category.html")
    cats_out = OUTPUT_DIR / "categories"
    cats_out.mkdir(exist_ok=True)

    for cat, cat_posts in sorted(by_category.items()):
        cat_slug = slugify(cat)
        cat_dir = cats_out / cat_slug
        cat_dir.mkdir(exist_ok=True)
        out_path = cat_dir / "index.html"
        out_path.write_text(
            cat_tmpl.render(**base_ctx(root_path="../../"), category=cat, posts=cat_posts),
            encoding="utf-8",
        )
        print(f"  ✓ dist/categories/{cat_slug}/index.html")

    # ── Render type pages ──────────────────────────────────────────────────────
    print("\nRendering types…")
    type_tmpl = env.get_template("type.html")
    types_out = OUTPUT_DIR / "types"
    types_out.mkdir(exist_ok=True)

    for t, type_posts in sorted(by_type.items()):
        type_slug = slugify(t)
        type_dir = types_out / type_slug
        type_dir.mkdir(exist_ok=True)
        out_path = type_dir / "index.html"
        out_path.write_text(
            type_tmpl.render(**base_ctx(root_path="../../"), post_type=t, posts=type_posts),
            encoding="utf-8",
        )
        print(f"  ✓ dist/types/{type_slug}/index.html")

    # ── Render links pages ─────────────────────────────────────────────────────
    if links:
        print("\nRendering links…")
        links_out = OUTPUT_DIR / "links"
        links_out.mkdir(exist_ok=True)

        links_map = {link["name"]: link["url"] for link in links}

        links_tmpl = env.get_template("links.html")
        (links_out / "index.html").write_text(
            links_tmpl.render(**base_ctx(root_path="../"), links=links),
            encoding="utf-8",
        )
        print("  ✓ dist/links/index.html")

        redirect_tmpl = env.get_template("links_redirect.html")
        go_out = links_out / "go"
        go_out.mkdir(exist_ok=True)
        (go_out / "index.html").write_text(
            redirect_tmpl.render(**base_ctx(root_path="../../"), links_map_json=json.dumps(links_map)),
            encoding="utf-8",
        )
        print("  ✓ dist/links/go/index.html")

    # ── Copy static assets ─────────────────────────────────────────────────────
    print("\nCopying static assets…")
    static_out = OUTPUT_DIR / "static"
    if static_out.exists():
        shutil.rmtree(static_out)
    shutil.copytree(STATIC_DIR, static_out)
    print(f"  ✓ dist/static/")

    if IMAGES_DIR.exists():
        images_out = OUTPUT_DIR / "images"
        if images_out.exists():
            shutil.rmtree(images_out)
        shutil.copytree(IMAGES_DIR, images_out)
        print(f"  ✓ dist/images/")

    # ── Summary ────────────────────────────────────────────────────────────────
    print(f"\nDone. {total_posts} post(s), {len(by_category)} categor{'y' if len(by_category) == 1 else 'ies'}, {len(by_type)} type{'s' if len(by_type) != 1 else ''}, {len(links)} link{'s' if len(links) != 1 else ''}.")
    print(f"Output: {OUTPUT_DIR.resolve()}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the blog.")
    args = parser.parse_args()
    build()
