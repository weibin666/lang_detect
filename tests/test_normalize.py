# -*- coding: utf-8 -*-
"""输入治理 sanitize 测试。"""
import pytest

import pipeline
from normalize import normalize_text, sanitize, strip_noise


def test_strip_url_email_mention():
    assert "http" not in sanitize("visit https://a.com/x?q=1 now")
    assert "@" not in sanitize("mail me a.b@test.com please")
    assert "@user" not in sanitize("@user hello there")


def test_strip_emoji():
    assert sanitize("good job 😀🎉🚀") == "good job"
    assert sanitize("国旗 🇨🇳 测试").replace(" ", "") == "国旗测试"


def test_markdown_link_keeps_text_drops_url():
    assert sanitize("see [docs](https://x.com/a) here") == "see docs here"
    assert "http" not in sanitize("![img](http://y.io/p.png) 文字")


def test_markdown_markers_removed():
    out = sanitize("# 标题 **加粗** `code` ~~删除~~")
    for ch in "#*`~":
        assert ch not in out


def test_nfkc_fullwidth_to_halfwidth():
    assert normalize_text("ＨＥＬＬＯ１２３") == "HELLO123"


def test_whitespace_collapsed():
    assert sanitize("a\n\n  b\t c") == "a b c"


def test_max_len_truncation():
    long = "a" * 200
    assert len(sanitize(long, max_len=50)) == 50


def test_empty():
    assert sanitize("") == ""
    assert sanitize(None) == ""


# ---- 与 pipeline 集成 ----
def test_pipeline_sanitizes_then_detects():
    r = pipeline.detect("Visit https://huawei.com 这是一段中文测试内容")
    assert "http" not in r["cleaned_text"]
    assert r["lang"] == "zh"


def test_pipeline_sanitize_can_be_disabled():
    r = pipeline.detect("https://x.com 你好世界测试内容", sanitize=False)
    assert "http" in r["cleaned_text"] or "x.com" in r["cleaned_text"]
