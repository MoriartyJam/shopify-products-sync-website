from datetime import datetime, timezone
from flask import Flask, Response, send_from_directory, request, jsonify
import os
import json
import urllib.request
import urllib.error

app = Flask(__name__, static_folder=".")


def get_public_base_url() -> str:
    configured = os.getenv("SITE_URL", "").strip()
    if configured:
        return configured.rstrip("/")
    return request.url_root.rstrip("/")


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


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
