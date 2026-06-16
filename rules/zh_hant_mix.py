# -*- coding: utf-8 -*-
"""规则：简繁混合（zh + zh-Hant）。

文本里同时出现简体特征字和繁体特征字 -> 判为简繁混合，
按两者数量多的一方返回主语种。
"""
NAME = "zh_hant_mix"


def detect(f):
    han = f["han"]
    if han == 0 or han < max(f["cyr"], f["latin"], f["hangul"]):
        return None
    simp, trad = f["simp_hits"], f["trad_hits"]
    if simp > 0 and trad > 0:
        lang = "zh-Hant" if trad >= simp else "zh"
        note = "简繁混合（简体特征字%d / 繁体特征字%d），主语种=%s" % (simp, trad, lang)
        conf = min(0.95, 0.7 + han / max(f["total"], 1) * 0.25)
        return {"lang": lang, "confidence": round(conf, 4),
                "detect_type": "rule", "method": "rule:" + NAME, "note": note}
    return None
