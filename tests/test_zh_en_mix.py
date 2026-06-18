# -*- coding: utf-8 -*-
"""中英混合规则测试。"""
import pytest

import rules
from config import ZH_EN_MIX_RATIO


def test_mixed_high_chinese_ratio_is_zh():
    r = rules.detect("我喜欢 apple")          # 中文占比 ~0.38 > 0.1
    assert r["lang"] == "zh"
    assert r["method"] == "rule:zh_en_mix"


def test_mixed_low_chinese_ratio_not_judged_chinese():
    # 中文占比 ~0.04 <= 0.1 -> zh_en_mix 不判中文（交给后续 en 规则/模型）
    r = rules.detect("hi hello world this is mostly english content here ok 你好")
    assert r is None or r["lang"] != "zh"  # 关键：不应判成中文


def test_mixed_traditional_is_zh_hant():
    r = rules.detect("Welcome 歡迎蒞臨參觀")   # 繁体特征明显
    assert r["lang"] == "zh-Hant"


def test_pure_chinese_not_handled_by_mix():
    r = rules.detect("纯中文内容测试一下")       # 无英文 -> 走 zh 规则
    assert r["lang"] == "zh"
    assert r["method"] != "rule:zh_en_mix"


def test_pure_english_not_handled_by_mix():
    r = rules.detect("this is a simple english sentence")
    assert r["method"] != "rule:zh_en_mix"


def test_threshold_value():
    assert ZH_EN_MIX_RATIO == 0.1
