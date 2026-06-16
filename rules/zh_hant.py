# -*- coding: utf-8 -*-
"""规则：繁体中文 zh-Hant（基于“繁体独有字符占比”）。

繁体独有字 = 不与简体共享的字（港台繁体通用）。
其占汉字的比例 > TRAD_RATIO(默认0.2) -> 判繁体。
低于阈值的模糊情况 -> 不在这里判，交给简体规则或兜底模型。
"""
from config import TRAD_RATIO

NAME = "zh_hant"


def detect(f):
    han = f["han"]
    if han == 0 or han < max(f["cyr"], f["latin"], f["hangul"]):
        return None
    ratio = f["trad_ratio"]
    if ratio <= TRAD_RATIO:
        return None
    conf = min(0.99, 0.7 + ratio * 0.25)
    return {"lang": "zh-Hant", "confidence": round(conf, 4),
            "detect_type": "rule", "method": "rule:" + NAME,
            "note": "繁体独有字占比 %.0f%%（繁%d / 汉字%d）" % (
                ratio * 100, f["trad_unique"], han)}
