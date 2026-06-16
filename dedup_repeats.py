# -*- coding: utf-8 -*-
"""
去除文本中的连续重复片段 / 连续重复词，只保留一个。

适用场景：语种检测前的文本清洗。脏文本里常见两类噪声——
  1. 连续重复的「片段 / 词」：w30039560w30039560w30039560
  2. 连续重复的「单字 / 字母」：你你你你...你好、wwwwwwwwwwwww this is a test

核心思路（正则）：
    (.+?)\\1{min_repeats-1,}  ->  \\1
  非贪婪地找出最小的重复单元，再把紧跟其后的若干次相同单元一起折叠成一次。

为什么默认 min_repeats=3（至少重复 3 次才折叠）：
  语种检测里，很多语言本身就有「叠词 / reduplication」，且只重复 2 次，
  例如 mama、papa、couscous、byebye、拜拜、谢谢、555。
  如果 2 次就折叠，会破坏这些合法词、丢失语种信息。
  而噪声片段往往重复很多次（示例里是 3 次、14 次、40 次），
  所以用 “>=3 次” 作为分界，既能清掉噪声，又能保住正常叠词。
  如需更激进/更保守，调 min_repeats 即可。
"""

import re

__all__ = ["collapse_repeats", "strip_digits"]

# 连续数字（含全角/各语言数字）；语种检测里数字无语种信息，先去掉减少噪声
_DIGITS_RE = re.compile(r"\d+", re.UNICODE)


def strip_digits(text):
    """去掉文本里连续的数字串（如 w30039560 -> w、电话 13800138000 -> 电话）。

    用 \\d+（Unicode 感知）匹配数字串并删除；只去数字，保留其余字符。
    """
    if not text:
        return text
    return _DIGITS_RE.sub("", text)


def collapse_repeats(text, min_repeats=3, max_unit_len=None, flags=re.DOTALL):
    """折叠连续重复的片段/词，每段重复只保留一个单元。

    参数:
        text:        待处理字符串。
        min_repeats: 连续重复达到几次才折叠（含本身），默认 3。
                     例：min_repeats=3 表示 "ABABAB"(3次) 会被折叠，
                     而 "ABAB"(2次) 保留不动。
        max_unit_len: 限制重复单元的最大长度（字符数），None 表示不限制。
                     设小一点可避免把很长的句子误当成重复单元。
        flags:       传给 re 的标志，默认 re.DOTALL 让 . 也能匹配换行。

    返回:
        处理后的字符串。

    示例:
        >>> collapse_repeats("w30039560w30039560w30039560")
        'w30039560'
        >>> collapse_repeats("你你你你你你你你你你好")
        '你好'
        >>> collapse_repeats("wwwwwwwwwwwwww this is a test")
        'w this is a test'
    """
    if not text:
        return text
    if min_repeats < 2:
        raise ValueError("min_repeats 至少为 2（重复 2 次才谈得上去重）")

    unit = ".+?" if max_unit_len is None else ".{{1,{}}}?".format(int(max_unit_len))
    # (unit)\1{min_repeats-1,}  ：单元本身 + 后面至少 (min_repeats-1) 次相同单元
    pattern = re.compile(r"({})\1{{{},}}".format(unit, min_repeats - 1), flags)
    return pattern.sub(r"\1", text)


if __name__ == "__main__":
    cases = [
        "w30039560w30039560w30039560",
        "你你你你你你你你你你你你你你你你你你你你你你你你你你你你你你你你你你你你你你好",
        "wwwwwwwwwwwwww this is a test",
        # 混合 / 多段噪声
        "哈哈哈哈哈哈这是一个测试abcabcabcabc结束了",
        # 应当被保留的合法叠词（只重复 2 次）
        "妈妈带我去拜拜，谢谢",
    ]
    for s in cases:
        print("原文:", s)
        print("结果:", collapse_repeats(s))
        print("-" * 40)
