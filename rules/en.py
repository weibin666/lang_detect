# -*- coding: utf-8 -*-
"""规则：英语 en（拉丁字母为主 + 英文停用词占比达标）。

拉丁系但不是英文（法德西等）-> 返回 None，交给模型兜底。
"""
from rules.script_utils import looks_english

NAME = "en"


def detect(f):
    latin = f["latin"]
    if latin == 0 or latin < max(f["cyr"], f["han"]):
        return None
    is_en, ratio = looks_english(f["text"])
    if not is_en:
        return None
    return {"lang": "en", "confidence": round(min(0.95, 0.6 + ratio), 4),
            "detect_type": "rule", "method": "rule:" + NAME,
            "note": "英文停用词占比 %.0f%%" % (ratio * 100)}
