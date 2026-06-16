# -*- coding: utf-8 -*-
"""规则：韩语 ko（谚文 Hangul，唯一无歧义脚本）。"""
NAME = "ko"


def detect(f):
    hangul = f["hangul"]
    if hangul == 0 or hangul < max(f["cyr"], f["latin"], f["han"]):
        return None
    conf = min(0.99, 0.7 + hangul / max(f["total"], 1) * 0.3)
    return {"lang": "ko", "confidence": round(conf, 4),
            "detect_type": "rule", "method": "rule:" + NAME, "note": "谚文"}
