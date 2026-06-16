# -*- coding: utf-8 -*-
"""规则：繁体中文 zh-Hant（汉字为主，且简繁判定为繁体）。"""
NAME = "zh_hant"


def detect(f):
    han = f["han"]
    if han == 0 or han < max(f["cyr"], f["latin"], f["hangul"]):
        return None
    lang, trad, simp = f["zh_variant"]
    if lang != "zh-Hant":
        return None
    conf = min(0.99, 0.7 + han / max(f["total"], 1) * 0.3)
    return {"lang": "zh-Hant", "confidence": round(conf, 4),
            "detect_type": "rule", "method": "rule:" + NAME,
            "note": "繁体信号 %d / 简体信号 %d" % (trad, simp)}
