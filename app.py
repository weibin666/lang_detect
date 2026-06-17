# -*- coding: utf-8 -*-
"""语种检测 Web 服务。

运行：
    python3 app.py
然后浏览器打开 http://127.0.0.1:5000
"""

import os

from flask import Flask, jsonify, render_template, request

from config import DEFAULT_MIN_REPEATS
from pipeline import detect, reload_all
from lang_names import name_of

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/detect", methods=["POST"])
def api_detect():
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text", "")
    dedup = bool(data.get("dedup", True))
    strip_digits = bool(data.get("strip_digits", True))
    sanitize = bool(data.get("sanitize", True))
    min_repeats = int(data.get("min_repeats", DEFAULT_MIN_REPEATS))
    # use_opencc: None=自动 / True=强制 OpenCC / False=强制特征字法
    use_opencc = data.get("use_opencc", None)

    r = detect(text, dedup=dedup, min_repeats=min_repeats, use_opencc=use_opencc,
               strip_digits=strip_digits, sanitize=sanitize)
    r["lang_name"] = name_of(r["lang"])
    if r.get("candidates"):
        r["candidates"] = [
            {"lang": c[0], "name": name_of(c[0]), "prob": round(c[1], 4)}
            for c in r["candidates"]
        ]
    if r.get("votes"):
        for v in r["votes"]:
            v["name"] = name_of(v["lang"])
    return jsonify(r)


@app.route("/api/reload", methods=["POST"])
def api_reload():
    """热重载术语库 + 词表（无需重启服务）。"""
    return jsonify({"ok": True, "reloaded": reload_all()})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=True)
