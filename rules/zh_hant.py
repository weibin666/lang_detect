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
    trad, simp, ratio = f["trad_unique"], f["simp_unique"], f["trad_ratio"]
    # 命中繁体的两种情形（简繁混合由 zh_hant_mix 在更前面处理）：
    #   1) 繁体独有字占比高 (> TRAD_RATIO)；
    #   2) 出现繁体独有字且无任何简体独有字 —— 低密度繁体也可靠（简体不会用繁体形）。
    if not (ratio > TRAD_RATIO or (trad > 0 and simp == 0)):
        return None
    conf = min(0.99, 0.7 + ratio * 0.25)
    return {"lang": "zh-Hant", "confidence": round(conf, 4),
            "detect_type": "rule", "method": "rule:" + NAME,
            "note": "繁体独有字 %d / 简体独有字 %d / 汉字 %d（占比%.0f%%）" % (
                trad, simp, han, ratio * 100)}
