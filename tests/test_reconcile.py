# -*- coding: utf-8 -*-
"""模型结果规则复核 reconcile 的单元测试（直接喂模型候选，不依赖真实模型）。"""
from reconcile import reconcile
from rules.script_utils import script_counts


def _rec(text, cands):
    return reconcile(text, cands, script_counts(text))


# A) 脚本族硬不匹配（任意置信度）
def test_high_conf_latin_misclassified_as_han():
    r = _rec("Qwxz Bttp Mlkj", [("zh", 0.99), ("ja", 0.0)])
    assert r["lang"] == "en"
    assert r["method"] == "rule:reconcile_script_latin"


def test_latin_misclassified_as_cyrillic():
    r = _rec("hello world test", [("ru", 0.8)])
    assert r["lang"] == "en"


def test_han_misclassified_as_korean():
    r = _rec("中文内容", [("ko", 0.7)])
    assert r["lang"] in ("zh", "zh-Hant")


# B) 纯汉字无假名 -> 中文（纠正模型 ja）
def test_han_no_kana_corrected_to_zh():
    r = _rec("短信", [("ja", 0.64), ("zh", 0.35)])
    assert r["lang"] == "zh"
    assert r["method"] == "rule:reconcile_han_zh"


def test_japanese_with_kana_not_corrected():
    # 含假名时 fam_text 仍 cjk，但应判 ja —— reconcile 不把它纠成 zh
    counts = script_counts("これは日本語です")
    r = reconcile("これは日本語です", [("ja", 0.9)], counts)
    assert r is None  # 模型 ja 与脚本一致，采纳


# C) 低置信同族复核
def test_low_conf_ascii_latin_to_en():
    r = _rec("Xqzt Bfgrm Kwjx", [("hu", 0.45), ("de", 0.2)])
    assert r["lang"] == "en"
    assert r["method"] == "rule:reconcile_latin_en"


def test_high_conf_real_language_preserved():
    assert _rec("bonjour le monde comment", [("fr", 0.99)]) is None
    assert _rec("das ist ein schoner tag", [("de", 0.98)]) is None


def test_low_conf_accented_latin_preserved():
    # 带变音符 -> 不当作乱码，交给模型
    assert _rec("café déjà vu", [("fr", 0.4)]) is None


def test_cyrillic_high_conf_preserved():
    assert _rec("привет как дела друзья", [("ru", 0.9)]) is None


def test_unknown_lang_family_not_touched():
    # 模型给一个脚本未知的语言、且与文本不冲突 -> 不动
    assert _rec("bonjour le monde", [("oc", 0.9)]) is None  # oc 未在 LANG_FAMILY
