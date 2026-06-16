# -*- coding: utf-8 -*-
"""规则：俄语 / 乌克兰语（含混合）。

西里尔为主时，按特征字母判定：
  乌克兰语独有 і ї є ґ；俄语独有 ы э ъ ё。
  两者都出现 -> 混合，按多者定主语种；
  只出现一方 -> 对应语种；
  都没有出现（模糊） -> 返回 None，交给模型层做 ru/uk 混合判定。
"""
NAME = "ru_uk_mix"


def detect(f):
    cyr = f["cyr"]
    if cyr == 0 or cyr < max(f["latin"], f["han"]):
        return None
    uk, ru = f["uk_hits"], f["ru_hits"]
    if uk == 0 and ru == 0:
        return None  # 模糊，交给模型层
    if uk > 0 and ru > 0:
        lang = "uk" if uk >= ru else "ru"
        note = "俄乌混合（uk特征%d / ru特征%d），主语种=%s" % (uk, ru, lang)
    else:
        lang = "uk" if uk > 0 else "ru"
        note = "乌克兰语特征 %d / 俄语特征 %d" % (uk, ru)
    conf = min(0.95, 0.6 + cyr / max(f["total"], 1) * 0.3)
    return {"lang": lang, "confidence": round(conf, 4),
            "detect_type": "rule", "method": "rule:" + NAME, "note": note}
