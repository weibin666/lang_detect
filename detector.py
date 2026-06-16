# -*- coding: utf-8 -*-
"""模型层（最后兜底）：fasttext lid.176 + 低资源级联(custom33 / langid)。

规则/词表/干预都在各自模块里；这里只负责“前面都没命中”时的模型判定。
对外提供 model_fallback(text) -> {lang, confidence, detect_type:'model', ...}。
"""

import os
import urllib.request

from cascade_models import cascade
from config import LATIN_EN_FALLBACK_CONF, LID176_PATH, LID176_URL
from rules.script_utils import cyrillic_ru_uk, script_counts, script_of

# ---------------------------------------------------------------------------
# fasttext 模型（lid.176）：懒加载 + 自动下载
# ---------------------------------------------------------------------------
_MODEL = None


def _ensure_model_file():
    if not os.path.exists(LID176_PATH):
        os.makedirs(os.path.dirname(LID176_PATH), exist_ok=True)
        urllib.request.urlretrieve(LID176_URL, LID176_PATH)
    return LID176_PATH


def get_model():
    """懒加载 fasttext 模型；首次调用会自动下载（约 1MB 的压缩版）。"""
    global _MODEL
    if _MODEL is None:
        import fasttext
        fasttext.FastText.eprint = lambda *a, **k: None
        _MODEL = fasttext.load_model(_ensure_model_file())
    return _MODEL


def model_predict(text, k=5):
    """返回 [(lang, prob), ...]，按概率降序。"""
    model = get_model()
    one_line = (text or "").replace("\n", " ").strip()
    labels, probs = model.predict(one_line, k=k)
    return [(lab.replace("__label__", ""), float(p)) for lab, p in zip(labels, probs)]


def _is_ascii_latin_dominant(text, counts):
    """是否为‘纯 ASCII 拉丁字母为主、无变音符’的文本。

    用于识别非真实语言的字母串（乱码/代号/无意义单词）：
    真实的非英语拉丁语言(法德西等)往往带变音符(é ü ñ ç…)，且模型置信度高；
    纯 ASCII 字母 + 模型低置信，更像是非语言的字母串。
    """
    latin = counts.get("latin", 0)
    total = sum(counts.values())
    if latin == 0 or latin < total * 0.9:      # 拉丁必须占绝对多数
        return False
    latin_chars = [c for c in text if script_of(ord(c)) == "latin"]
    if not latin_chars:
        return False
    ascii_ratio = sum(1 for c in latin_chars if ord(c) < 128) / len(latin_chars)
    return ascii_ratio >= 0.99                  # 几乎无变音符


def model_fallback(text):
    """模型兜底。返回 detect_type='model' 的结果 dict。"""
    counts = script_counts(text)
    try:
        cands = model_predict(text, k=5)
    except Exception as e:
        return {"lang": "und", "confidence": 0.0, "detect_type": "model",
                "method": "model:error", "note": "模型不可用: %s" % e, "scripts": counts}
    if not cands:
        return {"lang": "und", "confidence": 0.0, "detect_type": "model",
                "method": "model:empty", "scripts": counts}

    top1 = cands[0]

    # ru/uk 易混：模型 top1/top2 同为 {ru, uk} -> 混合，用特征字母挑主语种
    if set(c[0] for c in cands[:2]) == {"ru", "uk"}:
        lang, uk, ru = cyrillic_ru_uk(text)
        if uk == 0 and ru == 0:
            lang = top1[0]
        note = ("模型 top1/top2 为 ru+uk，判定为混合；主语种=%s"
                "（特征字母 uk:%d / ru:%d，模型 top1=%s）" % (lang, uk, ru, top1[0]))
        return {"lang": lang, "confidence": round(max(top1[1], 0.5), 4),
                "detect_type": "model", "method": "model+rule:ru-uk-mix",
                "candidates": cands, "note": note, "scripts": counts}

    # 低资源级联：lid.176 低置信 且命中 33 语种 -> custom33 -> langid
    casc = cascade(text, top1[0], top1[1])
    if casc is not None:
        return {"lang": casc["lang"], "confidence": casc["confidence"],
                "detect_type": "model", "method": casc["method"],
                "candidates": cands, "note": casc["note"], "scripts": counts}

    # 纯ASCII拉丁字母串 + 模型低置信 -> 非真实语言(乱码/代号)，默认 en
    # 走到这里说明前面 en 规则/词表都没命中，再低置信即视为非语言字母串
    if top1[1] < LATIN_EN_FALLBACK_CONF and _is_ascii_latin_dominant(text, counts):
        return {"lang": "en", "confidence": round(top1[1], 4),
                "detect_type": "rule", "method": "rule:latin_en_fallback",
                "candidates": cands, "scripts": counts,
                "note": "纯ASCII拉丁字母串且模型低置信(%.2f<%.2f)，非真实语言，默认英文"
                        % (top1[1], LATIN_EN_FALLBACK_CONF)}

    return {"lang": top1[0], "confidence": round(top1[1], 4),
            "detect_type": "model", "method": "model:fasttext",
            "candidates": cands, "note": "", "scripts": counts}
