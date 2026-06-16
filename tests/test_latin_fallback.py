# -*- coding: utf-8 -*-
"""纯ASCII拉丁字母串(非真实语言/乱码/代号) -> 默认 en 的兜底测试。"""
import os

import pytest

import pipeline
from config import LID176_PATH

needs_model = pytest.mark.skipif(not os.path.exists(LID176_PATH),
                                 reason="lid.176 模型未就绪")


@needs_model
@pytest.mark.parametrize("text", [
    "Xqzt Bfgrm Kwjxh Plkjm Zdrtv",     # 随机字母串
    "asdfgh qwerty zxcvbn hjkl",         # 键盘乱敲
    "Zentax Qorvi Blixar Trunel",        # 类品牌代号
])
def test_gibberish_latin_returns_en(text):
    r = pipeline.detect(text)
    assert r["lang"] == "en"
    assert r["method"] == "rule:latin_en_fallback"


@needs_model
@pytest.mark.parametrize("text, lang", [
    ("je ne sais pas ce que tu veux dire ici", "fr"),   # 无重音真法语
    ("das ist ein schoner tag heute gewesen", "de"),    # 真德语
    ("hola como estas hoy mi amigo querido", "es"),     # 真西语
    ("Ceci est une phrase en français", "fr"),          # 带重音法语
])
def test_real_languages_not_overridden(text, lang):
    r = pipeline.detect(text)
    assert r["lang"] == lang
    assert r["method"] != "rule:latin_en_fallback"
