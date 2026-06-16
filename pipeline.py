# -*- coding: utf-8 -*-
"""语种检测主编排。

单块检测顺序（第一个命中即返回，并带 detect_type 标识来源）：
    1. 强干预 intervene   detect_type=intervene
    2. 词表   dict_vote   detect_type=dict
    3. 规则   rules       detect_type=rule
    4. 模型   detector    detect_type=model

超长文本：先去重，再按 CHUNK_SIZE(默认1200) 分块，每块各跑一次单块检测，
最后按 (置信度 × 块字符数) 加权投票，得出最终主语种。
"""

import re

import dict_vote
import intervene
import rules
from dedup_repeats import collapse_repeats
from detector import model_fallback
from config import CHUNK_SIZE, DEFAULT_MIN_REPEATS
from rules.script_utils import script_counts


# ---------------------------------------------------------------------------
# 单块检测：四层串联
# ---------------------------------------------------------------------------
def detect_one(text, use_opencc=None):
    r = intervene.detect(text)            # 1. 强干预
    if r is None:
        r = dict_vote.detect(text)        # 2. 词表
    if r is None:
        r = rules.detect(text, use_opencc=use_opencc)  # 3. 规则
    if r is None:
        r = model_fallback(text)          # 4. 模型兜底
    r.setdefault("scripts", script_counts(text))
    r.setdefault("note", "")
    return r


# ---------------------------------------------------------------------------
# 分块
# ---------------------------------------------------------------------------
def chunk_text(text, size=CHUNK_SIZE):
    """按 size 分块；尽量在空白处断开，避免切断词。"""
    chunks, i, n = [], 0, len(text)
    while i < n:
        end = min(i + size, n)
        if end < n:
            # 在 [i, end] 内找最后一个空白处断开
            window = text[i:end]
            m = list(re.finditer(r"\s", window))
            if m and m[-1].start() > size * 0.6:
                end = i + m[-1].start() + 1
        chunks.append(text[i:end])
        i = end
    return chunks


# ---------------------------------------------------------------------------
# 投票
# ---------------------------------------------------------------------------
def _vote(chunk_results, chunks):
    """加权投票：每块给自己的 lang 投 (confidence × 块长) 的票。"""
    weights = {}        # lang -> 累计权重
    by_lang = {}        # lang -> [chunk result, ...]
    for r, c in zip(chunk_results, chunks):
        w = r["confidence"] * max(len(c), 1)
        weights[r["lang"]] = weights.get(r["lang"], 0.0) + w
        by_lang.setdefault(r["lang"], []).append(r)

    total = sum(weights.values()) or 1.0
    winner = max(weights, key=weights.get)
    win_results = by_lang[winner]

    # 最终置信度：胜出语种各块置信度的均值 × 得票占比
    avg_conf = sum(x["confidence"] for x in win_results) / len(win_results)
    share = weights[winner] / total
    conf = round(avg_conf * share, 4)

    # detect_type / method 取胜出语种里出现最多的来源
    types = [x["detect_type"] for x in win_results]
    detect_type = max(set(types), key=types.count)
    methods = [x["method"] for x in win_results if x["detect_type"] == detect_type]
    method = max(set(methods), key=methods.count) if methods else detect_type

    tally = sorted(
        ({"lang": l, "weight": round(w, 2), "share": round(w / total, 3)}
         for l, w in weights.items()),
        key=lambda d: d["weight"], reverse=True,
    )
    return {
        "lang": winner, "confidence": conf,
        "detect_type": detect_type, "method": method,
        "note": "分块投票：%d 块，胜出 %s 得票占比 %.0f%%" % (
            len(chunks), winner, share * 100),
        "votes": tally,
    }


# ---------------------------------------------------------------------------
# 对外主入口
# ---------------------------------------------------------------------------
def detect(text, dedup=True, min_repeats=None, use_opencc=None):
    if min_repeats is None:
        min_repeats = DEFAULT_MIN_REPEATS
    raw = text or ""
    cleaned = collapse_repeats(raw, min_repeats=min_repeats) if dedup else raw

    if len(cleaned) <= CHUNK_SIZE:
        r = detect_one(cleaned, use_opencc=use_opencc)
        r["cleaned_text"] = cleaned
        r["chunks"] = 1
        return r

    chunks = chunk_text(cleaned)
    chunk_results = [detect_one(c, use_opencc=use_opencc) for c in chunks]
    final = _vote(chunk_results, chunks)
    final["cleaned_text"] = cleaned
    final["chunks"] = len(chunks)
    final["scripts"] = script_counts(cleaned)
    return final


if __name__ == "__main__":
    samples = [
        "请用人民币支付，谢谢",                       # intervene zh
        "hello world today thanks everyone",          # dict/rule en
        "これは日本語のテストです。",                  # rule ja
        "我們在臺灣使用繁體中文",                       # rule zh-Hant
        "Привіт, це українська мова",                  # rule uk
        "Ceci est une longue phrase en français.",    # model fr
    ]
    for s in samples:
        r = detect(s)
        print("%-32s -> %-7s [%s] %s" % (
            s[:30], r["lang"], r.get("detect_type"), r.get("method")))
