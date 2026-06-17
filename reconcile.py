# -*- coding: utf-8 -*-
"""模型结果的“规则复核”层。

针对 badcase：短句/单词、拉丁+数字混合等，前面干预/词表/规则都没命中、
最后走模型预测时，模型（尤其短文本）容易误判。这里拿到模型结果后，用
**脚本/字符这种硬信号**再判一次，与模型结果比较，必要时覆盖：

  A. 脚本族不匹配（**任意置信度**）：模型预测语言的脚本族 ≠ 文本主脚本族，
     则模型必错（拉丁文本不可能是汉字/西里尔语言，哪怕模型 0.99）。按文本
     脚本族的默认语言纠正。
  B. 纯汉字无假名 -> 中文（cjk 内部 zh/ja：日语必有假名），纠正模型 ja 误判，
     **任意置信度**。
  C. 仅模型低置信(< RECONCILE_CONF)时的同族复核：
     纯ASCII拉丁(无变音符) -> en；西里尔有特征字母 -> ru/uk。

返回覆盖结果 dict（detect_type='rule'）或 None（采用模型原结果）。
"""

from config import RECONCILE_CONF
from rules.script_utils import cyrillic_ru_uk, script_of, zh_variant

CHINESE_LANGS = {"zh", "zh-Hant", "zh-Hans", "yue", "wuu"}

# 脚本 -> 脚本族
_FAMILY_OF_SCRIPT = {
    "han": "cjk", "hiragana": "cjk", "katakana": "cjk",
    "hangul": "hangul", "cyrillic": "cyrillic", "latin": "latin",
    "thai": "thai", "arabic": "arabic", "hebrew": "hebrew",
    "greek": "greek", "devanagari": "devanagari",
}

# 语言 -> 脚本族（只列脚本明确的常见语言；未列出的返回 None，不做不匹配纠正）
LANG_FAMILY = {}
for _l in ("zh zh-Hant zh-Hans yue wuu ja").split():
    LANG_FAMILY[_l] = "cjk"
LANG_FAMILY["ko"] = "hangul"
for _l in ("ru uk bg mk be kk ky mn tg").split():     # 明确用西里尔(塞尔维亚双文,略)
    LANG_FAMILY[_l] = "cyrillic"
LANG_FAMILY["th"] = "thai"
for _l in ("ar fa ur ps sd ckb").split():
    LANG_FAMILY[_l] = "arabic"
LANG_FAMILY["he"] = "hebrew"
LANG_FAMILY["el"] = "greek"
for _l in ("hi mr ne").split():
    LANG_FAMILY[_l] = "devanagari"
# 常见拉丁字母语言
for _l in ("en fr de es pt it nl pl tr vi id ms ro cs sk hu sv no da fi hr sl "
           "lt lv et ca eu gl is ga cy sw af sq tl la eo az uz").split():
    LANG_FAMILY[_l] = "latin"


def _text_family(counts):
    fam = {}
    for s, n in counts.items():
        f = _FAMILY_OF_SCRIPT.get(s)
        if f:
            fam[f] = fam.get(f, 0) + n
    return max(fam, key=fam.get) if fam else None


def _ascii_latin(text):
    lat = [c for c in text if script_of(ord(c)) == "latin"]
    return bool(lat) and sum(1 for c in lat if ord(c) < 128) / len(lat) >= 0.99


def _family_default(text, counts, fam):
    """某脚本族的默认语言。"""
    if fam == "latin":
        return "en"
    if fam == "cjk":
        if counts.get("hiragana", 0) + counts.get("katakana", 0) > 0:
            return "ja"
        return zh_variant(text)[0]          # zh / zh-Hant
    if fam == "cyrillic":
        return cyrillic_ru_uk(text)[0]      # ru / uk
    return {"hangul": "ko", "thai": "th", "arabic": "ar",
            "hebrew": "he", "greek": "el", "devanagari": "hi"}.get(fam)


def _ovr(lang, conf, case, model_lang, note):
    return {"lang": lang, "confidence": round(float(conf), 4),
            "detect_type": "rule", "method": "rule:reconcile_" + case,
            "model_lang": model_lang,
            "note": "复核：模型(%s)与脚本规则不一致，采用规则 -> %s（%s）"
                    % (model_lang, lang, note)}


def reconcile(text, cands, counts):
    """cands: 模型 [(lang,prob),...]；counts: 脚本计数。返回覆盖 dict 或 None。"""
    if not cands or sum(counts.values()) == 0:
        return None
    top_lang, top_conf = cands[0]
    fam_text = _text_family(counts)
    fam_lang = LANG_FAMILY.get(top_lang)

    # A) 脚本族硬不匹配（任意置信度）
    if fam_text and fam_lang and fam_text != fam_lang:
        d = _family_default(text, counts, fam_text)
        if d and d != top_lang:
            return _ovr(d, max(top_conf, 0.55), "script_" + fam_text, top_lang,
                        "文本主脚本族=%s，模型语言脚本族=%s" % (fam_text, fam_lang))

    # B) 纯汉字无假名 -> 中文（cjk 内部纠正模型 ja）
    if (fam_text == "cjk" and counts.get("hiragana", 0) + counts.get("katakana", 0) == 0
            and top_lang not in CHINESE_LANGS):
        lang = zh_variant(text)[0]
        return _ovr(lang, max(top_conf, 0.55), "han_zh", top_lang, "纯汉字无假名应为中文")

    # C) 仅低置信时的同族复核
    if top_conf >= RECONCILE_CONF:
        return None

    if fam_text == "latin" and _ascii_latin(text) and top_lang != "en":
        return _ovr("en", top_conf, "latin_en", top_lang,
                    "纯ASCII拉丁无变音符，非真实语言默认英文")

    if fam_text == "cyrillic":
        lang, uk, ru = cyrillic_ru_uk(text)
        if (uk or ru) and lang != top_lang:
            return _ovr(lang, top_conf, "cyrillic", top_lang,
                        "西里尔特征字母 uk:%d/ru:%d" % (uk, ru))

    return None
