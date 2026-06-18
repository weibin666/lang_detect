# -*- coding: utf-8 -*-
"""模型层（最后兜底）：fasttext lid.176 + 低资源级联(custom33 / langid)。

规则/词表/干预都在各自模块里；这里只负责“前面都没命中”时的模型判定。
对外提供 model_fallback(text) -> {lang, confidence, detect_type:'model', ...}。
"""

import os
import urllib.request

from cascade_models import cascade
from config import LID176_PATH, LID176_URL
from reconcile import reconcile
from rules.script_utils import cyrillic_ru_uk, script_counts

# ---------------------------------------------------------------------------
# fasttext 模型（lid.176）：懒加载 + 自动下载
# ---------------------------------------------------------------------------
_MODEL = None


def _ensure_model_file(allow_download=True):
    if not os.path.exists(LID176_PATH):
        if not allow_download:
            raise FileNotFoundError(
                "lid.176 模型缺失：%s。生产应把模型打进镜像/制品，"
                "或先运行 download_model()。" % LID176_PATH)
        os.makedirs(os.path.dirname(LID176_PATH), exist_ok=True)
        urllib.request.urlretrieve(LID176_URL, LID176_PATH)
    return LID176_PATH


def download_model():
    """显式下载 lid.176 到本地（构建镜像/制品时调用，避免运行时隐式联网下载）。"""
    path = _ensure_model_file(allow_download=True)
    size = os.path.getsize(path)
    if size < 100_000:                      # 压缩版约 ~938KB，过小说明下载不完整
        raise IOError("模型文件异常(仅 %d 字节)，可能下载不完整: %s" % (size, path))
    return path


def get_model():
    """懒加载 fasttext 模型；若本地缺失则下载（生产建议预先 warmup/打包）。"""
    global _MODEL
    if _MODEL is None:
        import fasttext
        fasttext.FastText.eprint = lambda *a, **k: None
        _MODEL = fasttext.load_model(_ensure_model_file())
    return _MODEL


def warmup():
    """启动预热：加载模型（触发一次下载/载入），避免首个请求的冷启动延迟。
    返回用到的模型列表。"""
    get_model()
    used = ["fasttext"]
    if cld3_available():
        used.append("cld3")
    return used


def model_predict(text, k=5):
    """返回 [(lang, prob), ...]，按概率降序。"""
    model = get_model()
    one_line = (text or "").replace("\n", " ").strip()
    labels, probs = model.predict(one_line, k=k)
    return [(lab.replace("__label__", ""), float(p)) for lab, p in zip(labels, probs)]


# ---------------------------------------------------------------------------
# CLD3（可选）：装了 gcld3 / pycld3 就自动参与集成，否则优雅降级为只用 fasttext。
# CLD3 在短文本上更稳，且自带 is_reliable / 原生 zh-Hant。
# ---------------------------------------------------------------------------
_CLD3 = None
_CLD3_TRIED = False


def _get_cld3():
    global _CLD3, _CLD3_TRIED
    if _CLD3_TRIED:
        return _CLD3
    _CLD3_TRIED = True
    try:
        import gcld3  # 优先 gcld3
        _CLD3 = gcld3.NNetLanguageIdentifier(min_num_bytes=0, max_num_bytes=2000)
        _CLD3_KIND = "gcld3"
    except Exception:
        try:
            import cld3  # pycld3
            _CLD3 = cld3
            _CLD3_KIND = "pycld3"
        except Exception:
            _CLD3 = None
    _get_cld3.kind = locals().get("_CLD3_KIND")
    return _CLD3


def cld3_available():
    return _get_cld3() is not None


def cld3_predict(text, k=5):
    """返回 [(lang, prob), ...]；CLD3 不可用时返回 None。"""
    c = _get_cld3()
    if c is None:
        return None
    one_line = (text or "").replace("\n", " ").strip()
    try:
        out = []
        if getattr(_get_cld3, "kind", None) == "gcld3":
            for r in c.FindTopNMostFreqLangs(one_line, k):
                if r and r.language and r.language != "und":
                    out.append((r.language, float(r.probability)))
        else:  # pycld3
            for r in c.get_frequent_languages(one_line, num_langs=k):
                if r and r.language and r.language != "und":
                    out.append((r.language, float(r.probability)))
        return out or None
    except Exception:
        return None


def _merge_predictions(ft, c3, w_ft=1.0, w_c3=1.0):
    """把两个模型的候选按归一化加权得分合并，返回降序 [(lang, score)]。"""
    def _norm(cands):
        s = sum(p for _, p in cands) or 1.0
        return {l: p / s for l, p in cands}
    a, b = _norm(ft or []), _norm(c3 or [])
    langs = set(a) | set(b)
    merged = {l: w_ft * a.get(l, 0.0) + w_c3 * b.get(l, 0.0) for l in langs}
    total = sum(merged.values()) or 1.0
    return sorted(((l, v / total) for l, v in merged.items()),
                  key=lambda kv: kv[1], reverse=True)


def ensemble_predict(text, k=5):
    """fasttext（+ 可选 CLD3）集成预测。返回 (cands, used_models)。"""
    ft = model_predict(text, k=k)
    c3 = cld3_predict(text, k=k)
    if not c3:
        return ft, ["fasttext"]
    return _merge_predictions(ft, c3), ["fasttext", "cld3"]


def model_fallback(text):
    """模型兜底。返回 detect_type='model' 的结果 dict。"""
    counts = script_counts(text)
    try:
        cands, used = ensemble_predict(text, k=5)
    except Exception as e:
        return {"lang": "und", "confidence": 0.0, "detect_type": "model",
                "method": "model:error", "note": "模型不可用: %s" % e, "scripts": counts}
    if not cands:
        return {"lang": "und", "confidence": 0.0, "detect_type": "model",
                "method": "model:empty", "scripts": counts}

    model_method = "model:" + "+".join(used)   # model:fasttext 或 model:fasttext+cld3
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

    # 规则复核：模型低置信/与脚本规则不一致时，用脚本/字符硬信号复核并可覆盖
    rec = reconcile(text, cands, counts)
    if rec is not None:
        rec["candidates"] = cands
        rec["scripts"] = counts
        return rec

    return {"lang": top1[0], "confidence": round(top1[1], 4),
            "detect_type": "model", "method": model_method,
            "candidates": cands, "note": "", "scripts": counts}
