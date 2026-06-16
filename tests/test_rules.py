# -*- coding: utf-8 -*-
"""规则层（rules 包）测试：每个语种/混合脚本的命中。"""
import pytest

import rules


@pytest.mark.parametrize("text, lang, rule", [
    ("これは日本語のテストです", "ja", "rule:zh_ja_mix"),
    ("私は学生です。今日はいい天気。", "ja", "rule:zh_ja_mix"),
    ("我们使用简体中文写文章", "zh", "rule:zh"),
    ("我們使用繁體中文寫文章", "zh-Hant", "rule:zh_hant"),
    ("我们一起去臺灣旅遊看風景", "zh-Hant", "rule:zh_hant_mix"),  # 简繁混合
    ("한국어 테스트입니다 반갑습니다", "ko", "rule:ko"),
    ("Привіт, це українська мова і її літери", "uk", "rule:ru_uk_mix"),
    ("Привет, это русский язык без особых", "ru", "rule:ru_uk_mix"),
    ("This is a simple test of the english detector", "en", "rule:en"),
])
def test_rule_hits(text, lang, rule):
    r = rules.detect(text)
    assert r is not None, "应命中规则但返回 None: %s" % text
    assert r["lang"] == lang
    assert r["method"] == rule
    assert r["detect_type"] == "rule"


@pytest.mark.parametrize("text", [
    "Ceci est une phrase en français",   # 法语：规则层不认，交给模型
    "Dies ist ein deutscher Satz hier",  # 德语
])
def test_rule_miss_for_other_latin(text):
    assert rules.detect(text) is None


def test_zh_ja_borrowed_kana_not_japanese():
    # 长中文里夹一个借用「の」，不应判成日语（规则层返回中文或不返回 ja）
    text = "这是一段很长的中文文案" * 3 + "の" + "继续中文内容" * 3
    r = rules.detect(text)
    assert r is not None
    assert r["lang"] in ("zh", "zh-Hant")
