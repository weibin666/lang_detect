# -*- coding: utf-8 -*-
"""规则：简体中文 zh。

汉字为主、出现简体独有字（不与繁体共享）、且未被前面的日语/繁体/简繁混合规则命中
-> 判简体。若汉字全是简繁共用字（无任何独有标记）则不在这里判，交给兜底模型。
"""
NAME = "zh"


def detect(f):
    han = f["han"]
    if han == 0 or han < max(f["cyr"], f["latin"], f["hangul"]):
        return None
    if f["simp_unique"] <= 0:
        return None  # 没有简体独有字 -> 模糊（全是共用字），交给模型
    conf = min(0.99, 0.7 + f["simp_ratio"] * 0.25 + han / max(f["total"], 1) * 0.1)
    return {"lang": "zh", "confidence": round(conf, 4),
            "detect_type": "rule", "method": "rule:" + NAME,
            "note": "简体独有字 %d / 汉字 %d" % (f["simp_unique"], han)}
