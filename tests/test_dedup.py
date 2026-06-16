# -*- coding: utf-8 -*-
"""去重 collapse_repeats 的测试。"""
import pytest

from dedup_repeats import collapse_repeats, strip_digits


@pytest.mark.parametrize("raw, expected", [
    ("w30039560w30039560w30039560", "w30039560"),          # 重复片段
    ("你你你你你你你你你你好", "你好"),                       # 重复单字(>=3)
    ("wwwwwwwwwwwwww this", "w this"),                      # 重复字母
    ("abcabcabc结束", "abc结束"),                            # 重复词
])
def test_collapse_repeats(raw, expected):
    assert collapse_repeats(raw) == expected


@pytest.mark.parametrize("raw", [
    "妈妈带我去拜拜",     # 2 次叠词应保留（mama/拜拜）
    "good food",         # oo 仅 2 次，保留
    "2011",              # 11 仅 2 次，保留
])
def test_preserves_double(raw):
    assert collapse_repeats(raw) == raw


def test_min_repeats_param():
    # min_repeats=2 时连 2 次重复也折叠
    assert collapse_repeats("妈妈", min_repeats=2) == "妈"
    assert collapse_repeats("妈妈", min_repeats=3) == "妈妈"


@pytest.mark.parametrize("raw, expected", [
    ("w30039560", "w"),                       # 字母后接长数字串
    ("电话13800138000请拨打", "电话请拨打"),     # 中文里夹电话号
    ("abc123def456", "abcdef"),               # 多段数字
    ("ＡＢ１２３", "ＡＢ"),                      # 全角数字也去掉
    ("no digits here", "no digits here"),      # 无数字不变
])
def test_strip_digits(raw, expected):
    assert strip_digits(raw) == expected


def test_pipeline_strips_digits():
    import pipeline
    r = pipeline.detect("w30039560w30039560 你好世界这是测试")
    assert not any(ch.isdigit() for ch in r["cleaned_text"])
    r2 = pipeline.detect("你好世界123", strip_digits=False)
    assert "123" in r2["cleaned_text"]
