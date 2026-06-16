# -*- coding: utf-8 -*-
"""
低资源语种的级联检测：自训 33 语种 fastText 模型 + langid.py 兜底。

级联触发条件（在 detector.detect 里调用）：
  当开源模型(lid.176) 的 top1 置信度 < LOW_CONF(0.3)，且 top1 语种 ∈ 这 33 个语种时，
  依次尝试：
    1) 自训 33 语种模型(custom33)         —— 置信度 >= 0.3 即返回（>0.6 视为高置信）
    2) 否则(<0.3) 再走 langid.py          —— 作为最后兜底返回
"""

import os

from config import (CUSTOM33_MODEL_PATH, HIGH_CONF, LANGS33_PATH, LOW_CONF)

# ------------------------------------------------------------------
# 你自训模型覆盖的 33 个低资源语种代码，从 langs33.txt 读取（一行一个，支持 # 注释）。
# 只用于“是否触发级联”的判断。路径/阈值见 config.py（可用环境变量覆盖）。
# 文件不存在时 LOW_RESOURCE_LANGS 为空集 -> 级联永不触发（安全：不会误判）。
# ------------------------------------------------------------------
def load_low_resource_langs(path=LANGS33_PATH):
    """从配置文件读取 33 语种代码集合。一行一个，# 之后为注释，空行忽略。"""
    langs = set()
    if not os.path.exists(path):
        return langs
    with open(path, encoding="utf-8") as f:
        for line in f:
            code = line.split("#", 1)[0].strip().lower()
            if code:
                langs.add(code)
    return langs


LOW_RESOURCE_LANGS = load_low_resource_langs()

_CUSTOM33 = None
_LANGID = None


# ------------------------------------------------------------------
# 1) 自训 33 语种 fastText 模型
# ------------------------------------------------------------------
def custom33_available():
    return os.path.exists(CUSTOM33_MODEL_PATH)


def _get_custom33():
    global _CUSTOM33
    if _CUSTOM33 is None:
        import fasttext
        fasttext.FastText.eprint = lambda *a, **k: None
        _CUSTOM33 = fasttext.load_model(CUSTOM33_MODEL_PATH)
    return _CUSTOM33


def custom33_predict(text):
    """返回 (lang, conf)；模型文件不存在或出错时返回 None（级联会跳过这步）。"""
    if not custom33_available():
        return None
    try:
        model = _get_custom33()
        one_line = (text or "").replace("\n", " ").strip()
        labels, probs = model.predict(one_line, k=1)
        if not labels:
            return None
        return labels[0].replace("__label__", ""), float(probs[0])
    except Exception:
        return None


# ------------------------------------------------------------------
# 2) langid.py 兜底（归一化概率 0~1）
# ------------------------------------------------------------------
def langid_available():
    try:
        import langid  # noqa: F401
        return True
    except Exception:
        return False


def _get_langid():
    global _LANGID
    if _LANGID is None:
        from langid.langid import LanguageIdentifier, model
        _LANGID = LanguageIdentifier.from_modelstring(model, norm_probs=True)
    return _LANGID


def langid_predict(text):
    """返回 (lang, conf)；不可用时返回 None。"""
    if not langid_available():
        return None
    try:
        lang, prob = _get_langid().classify((text or "").replace("\n", " ").strip())
        return lang, float(prob)
    except Exception:
        return None


# ------------------------------------------------------------------
# 级联主逻辑
# ------------------------------------------------------------------
def cascade(text, base_lang, base_conf):
    """开源模型给出 (base_lang, base_conf) 后，决定是否走级联。

    返回 dict {lang, confidence, method, note} 表示最终采纳的结果；
    若不触发级联 / 级联无更优结果，返回 None（调用方沿用开源模型结果）。
    """
    # 只有“低置信 且 命中 33 语种”才触发级联
    if not (base_conf < LOW_CONF and base_lang in LOW_RESOURCE_LANGS):
        return None

    trail = ["lid176(%s,%.2f)<%.2f" % (base_lang, base_conf, LOW_CONF)]

    # 第 1 步：自训 33 语种模型
    b = custom33_predict(text)
    if b is not None:
        lb, cb = b
        trail.append("custom33(%s,%.2f)" % (lb, cb))
        if cb >= LOW_CONF:
            lvl = "高置信" if cb > HIGH_CONF else "可接受"
            return {"lang": lb, "confidence": round(cb, 4),
                    "method": "cascade:custom33",
                    "note": "级联(%s)：自训模型 %s" % (" -> ".join(trail), lvl)}
    else:
        trail.append("custom33(unavailable)")

    # 第 2 步：langid 兜底
    c = langid_predict(text)
    if c is not None:
        lc, cc = c
        trail.append("langid(%s,%.2f)" % (lc, cc))
        lvl = "高置信" if cc > HIGH_CONF else "兜底"
        return {"lang": lc, "confidence": round(cc, 4),
                "method": "cascade:langid",
                "note": "级联(%s)：langid %s" % (" -> ".join(trail), lvl)}

    trail.append("langid(unavailable)")
    # 级联里所有模型都不可用 -> 让调用方沿用开源模型结果
    return None
