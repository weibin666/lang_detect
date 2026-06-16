# -*- coding: utf-8 -*-
"""规则：日语 / 中日混合。

区分 zh/ja 的关键是「是否含假名」——中文不用假名。
  - 含真假名             -> ja
  - 汉字+假名混排        -> 日语常态，主语种判 ja（并标注中日混合倾向）
  - 仅借用假名(の等)且占比极低 -> 不在这里判，交给中文规则
"""
NAME = "zh_ja_mix"


def detect(f):
    kana, han = f["kana"], f["han"]
    if kana == 0:
        return None
    kana_ratio = kana / (kana + han) if (kana + han) else 1.0
    # 仅借用假名且占比很低 -> 视作噪声，留给中文规则
    if not f["kana_genuine"] and kana_ratio < 0.15:
        return None

    if han > 0:
        note = "汉字+假名混排，主语种判日语（中日混合）"
    else:
        note = "含假名，判定日语"
    conf = min(0.99, 0.6 + kana_ratio)
    return {"lang": "ja", "confidence": round(conf, 4),
            "detect_type": "rule", "method": "rule:" + NAME, "note": note}
