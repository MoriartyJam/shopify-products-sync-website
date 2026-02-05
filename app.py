from flask import Flask, send_from_directory, request, jsonify
import os
import json
import urllib.request
import urllib.error

app = Flask(__name__, static_folder=".")


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)

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
