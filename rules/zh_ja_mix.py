# -*- coding: utf-8 -*-
"""规则：日语 / 中日混合（基于“日语独有字符占比”）。

日语独有字符 = 假名(平假名/片假名) + 和製漢字/新字体（不与简/繁中文共享）。
其占 CJK(汉字+假名) 的比例 > JA_RATIO(默认0.1) -> 判日语。
低于阈值（如中文里偶尔夹一个借用「の」）-> 不在这里判，交给后续规则/模型。
"""
from config import JA_RATIO

NAME = "zh_ja_mix"


def detect(f):
    cjk = f["cjk"]
    if cjk == 0 or cjk < max(f["cyr"], f["latin"], f["hangul"]):
        return None
    ratio = f["ja_ratio"]
    if ratio <= JA_RATIO:
        return None
    mixed = f["han"] > 0 and ratio < 0.6
    note = "日语独有字符占比 %.0f%%（假名%d+和製汉字%d / CJK%d）%s" % (
        ratio * 100, f["kana"], f["jp_kanji"], cjk, "，中日混排判主语种ja" if mixed else "")
    conf = min(0.99, 0.6 + ratio)
    return {"lang": "ja", "confidence": round(conf, 4),
            "detect_type": "rule", "method": "rule:" + NAME, "note": note}
