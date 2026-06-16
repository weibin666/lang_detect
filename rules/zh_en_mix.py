# -*- coding: utf-8 -*-
"""规则：中英混合。

文本同时含中文(汉字)和英文(拉丁字母)时：
  中文字符占比 = 汉字 / (汉字 + 拉丁) > ZH_EN_MIX_RATIO(默认0.1) -> 判中文。
  （繁体特征明显时返回 zh-Hant，否则 zh。）
否则（中文占比低）-> 返回 None，交给后续英文规则 / 兜底模型判断。
"""
from config import TRAD_RATIO, ZH_EN_MIX_RATIO

NAME = "zh_en_mix"


def detect(f):
    han, latin = f["han"], f["latin"]
    if han == 0 or latin == 0:
        return None  # 不是中英混合
    ratio = han / (han + latin)
    if ratio <= ZH_EN_MIX_RATIO:
        return None  # 中文占比低 -> 交给英文规则/模型
    lang = "zh-Hant" if f["trad_ratio"] > TRAD_RATIO else "zh"
    conf = min(0.95, 0.6 + ratio)
    return {"lang": lang, "confidence": round(conf, 4),
            "detect_type": "rule", "method": "rule:" + NAME,
            "note": "中英混合，中文占比 %.0f%%（汉字%d / 英文%d）-> %s" % (
                ratio * 100, han, latin, lang)}
