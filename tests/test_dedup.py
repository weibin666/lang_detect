# -*- coding: utf-8 -*-
"""去重 collapse_repeats 的测试。"""
import pytest

from dedup_repeats import collapse_repeats


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
