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
from dedup_repeats import collapse_repeats, strip_digits as _strip_digits
from detector import model_fallback
from config import CHUNK_SIZE, DEFAULT_MIN_REPEATS, RELIABLE_CONF
from normalize import sanitize as _sanitize, is_url_email_only
from config import URL_EMAIL_LANG
from rules.script_utils import script_counts


def reload_all():
    """热重载术语库 + 词表，返回各自条目数。供管理接口/定时任务调用。"""
    return {"intervene": intervene.reload_terms(), "dict": dict_vote.reload_dicts()}


# 纯数字 + 英文句号(.)（可含空白）：如版本号/IP/小数，直接判英文
_NUMERIC_DOT_RE = re.compile(r"^[\s.]*\d[\d\s.]*$")


def is_numeric_dot(text):
    """文本是否为“纯数字+英文句号”（至少含一个数字，其余只有数字/`.`/空白）。"""
    return bool(text) and _NUMERIC_DOT_RE.match(text) is not None


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
# 可靠性：能否信任到“可直接据此自动翻译”
# ---------------------------------------------------------------------------
# 这些方法是“非自然语言的兜底默认”，不算可靠的语言判定
_FALLBACK_METHODS = {
    "rule:empty", "rule:url_email", "rule:numeric_dot",
    "rule:reconcile_latin_en", "rule:reconcile_script_latin",
}


def _is_reliable(r):
    if r.get("lang") in (None, "und"):
        return False
    if r.get("method") in _FALLBACK_METHODS:
        return False
    if r.get("detect_type") == "model":
        return r.get("confidence", 0.0) >= RELIABLE_CONF
    return True   # intervene / dict / 脚本类规则：命中即视为可靠


# ---------------------------------------------------------------------------
# 对外主入口
# ---------------------------------------------------------------------------
def _language_breakdown(r):
    """标准化的多语种占比输出 [{lang, proportion}]，降序。
    超长分块时取投票占比（真实混合分布）；否则单一语种占比 1.0。"""
    votes = r.get("votes")
    if votes:
        return [{"lang": v["lang"], "proportion": v["share"]} for v in votes]
    return [{"lang": r["lang"], "proportion": 1.0}]


def detect(text, **kwargs):
    """对外入口：核心检测 + 统一补齐 reliable / languages / candidates 字段。"""
    r = _detect_core(text, **kwargs)
    r["reliable"] = _is_reliable(r)
    r["languages"] = _language_breakdown(r)
    # 统一始终带候选：规则/词表/干预路径没有模型候选时，用主结果占位
    if not r.get("candidates"):
        r["candidates"] = [(r["lang"], r["confidence"])]
    return r


def _detect_core(text, dedup=True, min_repeats=None, use_opencc=None, strip_digits=True,
                 sanitize=True):
    if min_repeats is None:
        min_repeats = DEFAULT_MIN_REPEATS

    original = text or ""
    # 整段就是 URL/邮箱（无自然语言内容）-> 直接给定语种（默认 en，可配 und）
    if is_url_email_only(original):
        return {"lang": URL_EMAIL_LANG, "confidence": 0.9, "detect_type": "rule",
                "method": "rule:url_email", "note": "整段为 URL/邮箱，无自然语言内容",
                "cleaned_text": original.strip(), "chunks": 1, "scripts": {}}

    # 输入治理：截断超长 + 去噪(URL/email/@/emoji/markdown) + NFKC归一化 + 折叠空白
    raw = _sanitize(original) if sanitize else original

    # 治理后无任何字母/数字（纯 emoji / 纯标点 / 去噪后无内容）-> 无可识别语言
    if not re.search(r"[^\W_]", raw, re.UNICODE):
        return {"lang": "und", "confidence": 0.0, "detect_type": "rule",
                "method": "rule:empty", "note": "无可识别的语言内容",
                "cleaned_text": raw.strip(), "chunks": 1, "scripts": {}}

    # 特例：纯数字+英文句号（版本号/IP/小数等）-> 直接英文（在去数字之前判断）
    if is_numeric_dot(raw):
        return {"lang": "en", "confidence": 0.9, "detect_type": "rule",
                "method": "rule:numeric_dot", "note": "纯数字+英文句号，直接判英文",
                "cleaned_text": raw, "chunks": 1, "scripts": {}}

    cleaned = raw
    if strip_digits:                       # 先去掉连续数字（无语种信息）
        cleaned = _strip_digits(cleaned)
    if dedup:                              # 再折叠连续重复
        cleaned = collapse_repeats(cleaned, min_repeats=min_repeats)

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
