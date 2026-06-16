# -*- coding: utf-8 -*-
"""主编排测试：四层顺序 / detect_type / 去重 / 超长分块投票。"""
import os

import pytest

import pipeline
from config import CHUNK_SIZE, LID176_PATH

_HAS_MODEL = os.path.exists(LID176_PATH)
needs_model = pytest.mark.skipif(not _HAS_MODEL, reason="lid.176 模型未就绪")


# ---------------- detect_type 来源标识 + 四层顺序 ----------------
@pytest.mark.parametrize("text, lang, detect_type", [
    ("请用人民币支付，谢谢", "zh", "intervene"),       # 第1层
    ("hello world today thanks", "en", "dict"),         # 第2层
    ("한국어를 배우고 있습니다 오늘", "ko", "rule"),     # 第3层(无 ko 词表 -> 走规则)
])
def test_layer_and_detect_type(text, lang, detect_type):
    r = pipeline.detect(text)
    assert r["lang"] == lang
    assert r["detect_type"] == detect_type
    assert "method" in r and r["method"]


@needs_model
def test_model_fallback_french():
    r = pipeline.detect("Ceci est une longue phrase écrite en français.")
    assert r["lang"] == "fr"
    assert r["detect_type"] == "model"


def test_detect_type_always_present():
    for t in ["请用人民币支付", "hello world today", "これは日本語です", "我們繁體"]:
        assert pipeline.detect(t).get("detect_type") in {
            "intervene", "dict", "rule", "model"}


# ---------------- 纯数字+英文句号 -> 直接英文 ----------------
@pytest.mark.parametrize("text", [
    "123.456.789", "3.14", "1.2.3", "192.168.0.1", "2024.01.01", "12345", "1. 2. 3",
])
def test_numeric_dot_returns_en(text):
    r = pipeline.detect(text)
    assert r["lang"] == "en"
    assert r["method"] == "rule:numeric_dot"
    assert r["cleaned_text"] == text  # 未被去数字破坏


@pytest.mark.parametrize("text", [
    "hello 1.2",   # 含字母
    "你好 3.14",    # 含中文
    "...",          # 无数字
])
def test_numeric_dot_not_triggered(text):
    r = pipeline.detect(text)
    assert r["method"] != "rule:numeric_dot"


# ---------------- 去重在 pipeline 内生效（关掉去数字以单独验证去重） ----------------
def test_dedup_applied():
    r = pipeline.detect("w30039560w30039560w30039560 你好世界这是测试内容",
                        strip_digits=False)
    assert r["cleaned_text"].count("w30039560") == 1
    assert r["lang"] == "zh"


def test_dedup_can_be_disabled():
    r = pipeline.detect("w30039560w30039560w30039560 你好",
                        dedup=False, strip_digits=False)
    assert r["cleaned_text"].count("w30039560") == 3


# ---------------- 超长分块 + 投票 ----------------
def _long(prefix_fmt, n):
    return "".join(prefix_fmt % i for i in range(n))


def test_chunking_triggers():
    long_zh = _long("第%d句：我们今天讨论一个重要话题。", 80)
    assert len(long_zh) > CHUNK_SIZE
    r = pipeline.detect(long_zh, dedup=False)
    assert r["chunks"] > 1
    assert r["lang"] == "zh"
    assert "votes" in r
    # 票重总占比应为 1
    assert abs(sum(v["share"] for v in r["votes"]) - 1.0) < 0.02


def test_short_text_single_chunk():
    r = pipeline.detect("我们使用简体中文")
    assert r["chunks"] == 1
    assert "votes" not in r


@needs_model
def test_voting_picks_majority_language():
    # 多数英文 + 少量俄文 -> 主语种应为英文
    mixed = _long("Sentence %d about general topics in english. ", 50) + \
            _long("Предложение %d на русском. ", 10)
    r = pipeline.detect(mixed, dedup=False)
    assert r["chunks"] > 1
    assert r["lang"] == "en"
