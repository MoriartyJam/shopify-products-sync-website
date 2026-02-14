from datetime import datetime, timezone
from flask import Flask, Response, send_from_directory, request, jsonify, redirect, render_template, abort
import os
import json
import urllib.request
import urllib.error
from urllib.parse import urlparse

app = Flask(__name__, static_folder=".")
BLOG_CONTENT_DIR = os.path.join(app.root_path, "content", "blog")


def get_public_base_url() -> str:
    configured = os.getenv("SITE_URL", "").strip()
    if configured:
        return configured.rstrip("/")
    return request.url_root.rstrip("/")


def _parse_iso_datetime(value: str) -> datetime:
    raw = (value or "").strip()
    if not raw:
        raise ValueError("Empty datetime")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_blog_posts() -> list[dict]:
    if not os.path.isdir(BLOG_CONTENT_DIR):
        return []

    posts = []
    for name in os.listdir(BLOG_CONTENT_DIR):
        if not name.endswith(".json"):
            continue

        path = os.path.join(BLOG_CONTENT_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                item = json.load(f)
        except Exception:
            continue

        slug = str(item.get("slug", "")).strip().strip("/")
        title = str(item.get("title", "")).strip()
        description = str(item.get("description", "")).strip()
        content_html = str(item.get("content_html", "")).strip()
        if not slug or not title or not description or not content_html:
            continue

        try:
            published_dt = _parse_iso_datetime(str(item.get("published_at", "")).strip())
        except Exception:
            continue

        updated_raw = str(item.get("updated_at", "")).strip()
        try:
            updated_dt = _parse_iso_datetime(updated_raw) if updated_raw else published_dt
        except Exception:
            updated_dt = published_dt

        keywords = item.get("keywords") or []
        if not isinstance(keywords, list):
            keywords = []
        keywords = [str(k).strip() for k in keywords if str(k).strip()]

        posts.append(
            {
                "slug": slug,
                "title": title,
                "description": description,
                "content_html": content_html,
                "keywords": keywords,
                "published_at": published_dt,
                "updated_at": updated_dt,
                "published_iso": published_dt.date().isoformat(),
                "updated_iso": updated_dt.date().isoformat(),
                "published_human": published_dt.strftime("%d.%m.%Y"),
                "updated_human": updated_dt.strftime("%d.%m.%Y"),
            }
        )

    posts.sort(key=lambda p: p["published_at"], reverse=True)
    return posts


def get_request_scheme() -> str:
    # Respect reverse proxy headers when present.
    forwarded = request.headers.get("X-Forwarded-Proto", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.scheme


@app.before_request
def enforce_canonical_url():
    if request.method not in ("GET", "HEAD"):
        return None

    configured = os.getenv("SITE_URL", "").strip()
    if not configured:
        return None

    target = urlparse(configured)
    if not target.scheme or not target.netloc:
        return None

    req_scheme = get_request_scheme()
    req_host = request.host.split(":")[0].lower()
    target_host = target.netloc.split(":")[0].lower()

    # Normalize /index.html to root and enforce canonical host/scheme.
    normalized_path = "/" if request.path == "/index.html" else request.path
    needs_redirect = (
        req_scheme.lower() != target.scheme.lower()
        or req_host != target_host
        or normalized_path != request.path
    )

    if not needs_redirect:
        return None

    query = request.query_string.decode("utf-8")
    destination = f"{target.scheme}://{target.netloc}{normalized_path}"
    if query:
        destination = f"{destination}?{query}"
    return redirect(destination, code=301)


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/index.html")
def index_html():
    return redirect("/", code=301)


@app.route("/blog")
def blog_index():
    base_url = get_public_base_url()
    posts = load_blog_posts()
    return render_template(
        "blog_index.html",
        posts=posts,
        canonical_url=f"{base_url}/blog",
        page_url=f"{base_url}/blog",
        site_url=base_url,
    )


@app.route("/blog/")
def blog_index_slash():
    return redirect("/blog", code=301)


@app.route("/blog/<slug>")
def blog_post(slug):
    base_url = get_public_base_url()
    normalized_slug = (slug or "").strip().strip("/")
    posts = load_blog_posts()
    post = next((p for p in posts if p["slug"] == normalized_slug), None)
    if not post:
        abort(404)

    return render_template(
        "blog_post.html",
        post=post,
        canonical_url=f"{base_url}/blog/{post['slug']}",
        page_url=f"{base_url}/blog/{post['slug']}",
        site_url=base_url,
    )


@app.route("/blog/<slug>/")
def blog_post_slash(slug):
    normalized_slug = (slug or "").strip().strip("/")
    if not normalized_slug:
        return redirect("/blog", code=301)
    return redirect(f"/blog/{normalized_slug}", code=301)


@app.route("/robots.txt")
def robots():
    base_url = get_public_base_url()
    body = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            f"Sitemap: {base_url}/sitemap.xml",
            "",
        ]
    )
    return Response(body, mimetype="text/plain; charset=utf-8")


@app.route("/sitemap.xml")
def sitemap():
    base_url = get_public_base_url()
    index_path = os.path.join(app.root_path, "index.html")
    updated_at = datetime.fromtimestamp(os.path.getmtime(index_path), tz=timezone.utc).date().isoformat()
    posts = load_blog_posts()

    rows = [
        f"""  <url>
    <loc>{base_url}/</loc>
    <lastmod>{updated_at}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>"""
    ]

    if posts:
        latest_blog = max(p["updated_iso"] for p in posts)
        rows.append(
            f"""  <url>
    <loc>{base_url}/blog</loc>
    <lastmod>{latest_blog}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>"""
        )

    for post in posts:
        rows.append(
            f"""  <url>
    <loc>{base_url}/blog/{post['slug']}</loc>
    <lastmod>{post['updated_iso']}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>"""
        )

    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{os.linesep.join(rows)}
</urlset>
"""
    return Response(body, mimetype="application/xml; charset=utf-8")


@app.route("/api/lead", methods=["POST"])
def lead():
    endpoint = os.getenv("QW_LEADS_ENDPOINT", "").strip()
    if not endpoint:
        return jsonify({"result": "error", "message": "QW_LEADS_ENDPOINT is not set"}), 500

    payload = request.get_json(silent=True) or {}
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json;charset=UTF-8"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8") if resp else ""
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8") if e.fp else ""
        return jsonify({"result": "error", "message": f"HTTP {e.code}", "details": raw}), 502
    except Exception as e:
        return jsonify({"result": "error", "message": str(e)}), 502

    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and data.get("result") == "error":
                return jsonify(data), 502
        except Exception:
            pass

    return jsonify({"result": "ok"})


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=False)
