# -*- coding: utf-8 -*-
"""强干预层 + 词表层测试（依赖 resources/ 下的示例数据）。"""
import pytest

import dict_vote
import intervene


# ---------------- 强干预 ----------------
def test_intervene_contains_zh():
    r = intervene.detect("请用人民币支付")
    assert r is not None
    assert r["lang"] == "zh"
    assert r["detect_type"] == "intervene"


def test_intervene_contains_en():
    r = intervene.detect("My Social Security Number is private")
    assert r is not None
    assert r["lang"] == "en"
    assert r["detect_type"] == "intervene"


def test_intervene_miss():
    assert intervene.detect("完全无关的普通文本一段") is None


# ---------------- 词表 ----------------
@pytest.mark.parametrize("text, lang", [
    ("你好 我们 今天 谢谢", "zh"),
    ("hello world today thanks", "en"),
    ("bonjour merci le monde", "fr"),
])
def test_dict_hits(text, lang):
    r = dict_vote.detect(text)
    assert r is not None, "词表应命中: %s" % text
    assert r["lang"] == lang
    assert r["detect_type"] == "dict"


def test_dict_miss_below_threshold():
    # 命中数不足 MIN_DICT_HITS -> None
    assert dict_vote.detect("你好 xyzqq") is None
    assert dict_vote.detect("zzz qqq vvv") is None
