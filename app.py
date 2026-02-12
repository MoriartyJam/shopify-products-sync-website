from datetime import datetime, timezone
from flask import Flask, Response, send_from_directory, request, jsonify, redirect
import os
import json
import urllib.request
import urllib.error
from urllib.parse import urlparse

app = Flask(__name__, static_folder=".")


def get_public_base_url() -> str:
    configured = os.getenv("SITE_URL", "").strip()
    if configured:
        return configured.rstrip("/")
    return request.url_root.rstrip("/")


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


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)


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
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{base_url}/</loc>
    <lastmod>{updated_at}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=False)
