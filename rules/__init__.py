# -*- coding: utf-8 -*-
"""规则层调度：按顺序跑各语种/混合规则脚本，第一个命中的返回。

顺序很重要：先处理含假名(日)、再简繁混合、再单一简/繁、谚文、俄乌、英文。
每个规则脚本是独立模块，返回 {lang, confidence, detect_type:'rule', method, note} 或 None。
"""
from rules import en, ko, ru_uk_mix, zh, zh_en_mix, zh_hant, zh_hant_mix, zh_ja_mix
from rules.script_utils import features

# 调度顺序
_PIPELINE = [
    zh_ja_mix,    # 假名 -> 日语 / 中日混合
    zh_hant_mix,  # 简繁混合
    zh_hant,      # 纯繁体
    zh,           # 纯简体
    zh_en_mix,    # 中英混合：中文占比 > 阈值 -> 中文，否则交给 en/模型
    ko,           # 谚文 -> 韩语
    ru_uk_mix,    # 西里尔 -> 俄/乌（含混合）
    en,           # 拉丁 + 英文停用词 -> 英语
]


def detect(text, use_opencc=None):
    """跑规则层。命中返回结果 dict（含 scripts），否则返回 None。"""
    f = features(text, use_opencc=use_opencc)
    for mod in _PIPELINE:
        r = mod.detect(f)
        if r is not None:
            r["scripts"] = f["counts"]
            return r
    return None
