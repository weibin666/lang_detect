# -*- coding: utf-8 -*-
"""基于“独有字符占比”的繁体/日语强规则测试。"""
import pytest

import rules
from config import JA_RATIO, TRAD_RATIO
from rules.script_utils import features


# ---------------- 日语：独有字符占比 > 0.1 ----------------
def test_japanese_by_kana_ratio():
    r = rules.detect("これは日本語のテストです。")
    assert r["lang"] == "ja" and r["method"] == "rule:zh_ja_mix"


def test_japanese_kanji_with_kana():
    f = features("私は東京に住んでいます")
    assert f["ja_ratio"] > JA_RATIO
    assert rules.detect("私は東京に住んでいます")["lang"] == "ja"


def test_borrowed_kana_below_threshold_not_japanese():
    # 长中文 + 一个借用「の」：日语占比远低于 0.1 -> 不判日语
    text = "这是一段很长的简体中文文案内容用来测试占比" * 2 + "の"
    f = features(text)
    assert f["ja_ratio"] <= JA_RATIO
    r = rules.detect(text)
    assert r is None or r["lang"] in ("zh", "zh-Hant")


# ---------------- 繁体：独有字符占比 > 0.2 ----------------
def test_traditional_above_threshold():
    text = "我們在臺灣使用繁體中文書寫"
    f = features(text)
    assert f["trad_ratio"] > TRAD_RATIO
    assert rules.detect(text)["lang"] == "zh-Hant"


def test_simplified_not_traditional():
    f = features("我们使用简体中文")
    assert f["trad_ratio"] == 0.0
    assert rules.detect("我们使用简体中文")["lang"] == "zh"


# ---------------- 其他情况 -> 交给模型（规则层返回 None） ----------------
def test_shared_only_han_defers_to_model():
    # 全是简繁共用字、无任何独有标记、无假名 -> 规则层不判，交给模型
    f = features("你好世界")
    assert f["trad_ratio"] == 0 and f["simp_ratio"] == 0 and f["ja_ratio"] == 0
    assert rules.detect("你好世界") is None
