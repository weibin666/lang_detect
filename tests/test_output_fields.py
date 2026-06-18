# -*- coding: utf-8 -*-
"""对标谷歌新增的输出字段：reliable / languages / candidates，以及 HTML 去除、模型预热。"""
import pytest

import pipeline
from normalize import sanitize, strip_html


# ---- reliable ----
@pytest.mark.parametrize("text, reliable", [
    ("请用人民币支付", True),          # intervene
    ("这是一段中文内容测试", True),       # rule
    ("https://x.com", False),         # url 默认 en，不可靠
    ("😀🎉", False),                   # und
    ("Qwxz Bttp Mlkj", False),        # 乱码兜底 en，不可靠
])
def test_reliable_flag(text, reliable):
    assert pipeline.detect(text)["reliable"] is reliable


# ---- languages 占比 ----
def test_languages_single():
    r = pipeline.detect("这是一段纯中文内容")
    assert r["languages"][0]["lang"] == r["lang"]
    assert abs(sum(x["proportion"] for x in r["languages"]) - 1.0) < 1e-6


def test_languages_mixed_long():
    text = ("".join("English sentence number %d here. " % i for i in range(40))
            + "".join("这是第%d句中文内容。" % i for i in range(40)))
    r = pipeline.detect(text, dedup=False)
    langs = {x["lang"] for x in r["languages"]}
    assert "en" in langs and "zh" in langs
    assert abs(sum(x["proportion"] for x in r["languages"]) - 1.0) < 1e-6


# ---- candidates 始终存在 ----
@pytest.mark.parametrize("text", ["请用人民币支付", "这是中文", "https://x.com", "hello world today"])
def test_candidates_always_present(text):
    assert pipeline.detect(text).get("candidates")


# ---- HTML 去除 ----
def test_strip_html_tags_and_entities():
    assert strip_html("<p>你好<b>世界</b></p>").strip().replace(" ", "") == "你好世界"
    assert "&nbsp;" not in sanitize("a&nbsp;b")
    assert "alert" not in sanitize("<script>alert(1)</script>正文内容")


def test_html_does_not_break_detection():
    assert pipeline.detect("<div class='x'>这是一段中文测试内容</div>")["lang"] == "zh"


# ---- warmup / download ----
def test_warmup_returns_models():
    from detector import warmup
    used = warmup()
    assert "fasttext" in used
