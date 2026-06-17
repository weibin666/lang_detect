# -*- coding: utf-8 -*-
"""第二步：词表判断（区分空格语言 / 非空格语言，两路打分后综合判断）。

每个语种一个 CSV：resources/dict/<lang>.csv，每行 `词,词频`（兼容空格/制表分隔）。

为什么分两路：
  - 空格语言（en/fr/ru/de... 用空格分词）：按“整词命中”打分。
  - 非空格语言（zh/zh-Hant/ja/th/lo/km/my/bo... 不用空格）：按“子串命中”打分。
  两路各自得到一个降序结果，例如非空格路：{"zh":178,"th":3}，空格路：{"en":40,"fr":5}，
  再用“覆盖率”（识别量/相应字符数）把两路放到同一标尺上综合比较，选出主语种。

不确定（覆盖率不足 / 组内次高太接近 / 两路势均力敌）-> 返回 None，交给后续规则/模型兜底。
"""

import csv
import glob
import math
import os
import re
import time

from config import (DICT_DIR, DICT_MARGIN, HIGH_CONF, MIN_DICT_COVERAGE,
                    MIN_DICT_HITS, RESOURCE_RELOAD_TTL)
from rules.script_utils import script_of

# 非空格语言（不用空格分词，按子串匹配）
NON_SPACE_LANGS = {"zh", "zh-Hant", "yue", "ja", "th", "lo", "km", "my", "bo"}
# 这些脚本的字符算作“非空格字符”（用于覆盖率分母）
_NON_SPACE_SCRIPTS = {"han", "hiragana", "katakana", "thai"}

_DICTS = None
_DICTS_LOADED_AT = 0.0
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def _parse_row(row):
    if len(row) >= 2:
        word, freq = row[0], row[1]
    else:
        parts = re.split(r"[\s,]+", row[0].strip())
        if len(parts) < 2:
            return None
        word, freq = parts[0], parts[1]
    word = word.strip().lower()
    try:
        freq = float(freq)
    except ValueError:
        freq = 1.0
    return (word, freq) if word else None


def load_dicts(force=False):
    """{lang: {entry_lower: freq}}。按 TTL 自动热更新；force=True 立即重载。"""
    global _DICTS, _DICTS_LOADED_AT
    now = time.time()
    stale = (RESOURCE_RELOAD_TTL > 0 and now - _DICTS_LOADED_AT >= RESOURCE_RELOAD_TTL)
    if _DICTS is not None and not force and not stale:
        return _DICTS
    dicts = {}
    if os.path.isdir(DICT_DIR):
        for path in glob.glob(os.path.join(DICT_DIR, "*.csv")):
            lang = os.path.splitext(os.path.basename(path))[0]
            entries = {}
            with open(path, encoding="utf-8") as f:
                for row in csv.reader(f):
                    if not row or row[0].lstrip().startswith("#"):
                        continue
                    pr = _parse_row(row)
                    if pr:
                        entries[pr[0]] = pr[1]
            if entries:
                dicts[lang] = entries
    _DICTS = dicts
    _DICTS_LOADED_AT = now
    return _DICTS


def reload_dicts():
    """立即重载词表，返回各语种词条数。"""
    dicts = load_dicts(force=True)
    return {lang: len(d) for lang, d in dicts.items()}


def _w(freq):
    return math.log(1 + freq)


def _score_space(text):
    """空格语言：整词命中。返回 {lang: (score, hits)} 和 词数。"""
    low = text.lower()
    tokens = _WORD_RE.findall(low)
    token_set = set(tokens)
    out = {}
    for lang, d in load_dicts().items():
        if lang in NON_SPACE_LANGS:
            continue
        score, hits = 0.0, 0
        for entry, freq in d.items():
            if " " in entry:                      # 短语条目用子串
                if entry in low:
                    score += _w(freq); hits += 1
            elif entry in token_set:              # 单词条目整词命中
                score += _w(freq); hits += 1
        if hits:
            out[lang] = (score, hits)
    return out, len(tokens)


def _score_non_space(text):
    """非空格语言：子串命中。返回 {lang: (score, hits, cover_chars)} 和 非空格字符数。"""
    low = text.lower()
    ns_chars = sum(1 for c in text if script_of(ord(c)) in _NON_SPACE_SCRIPTS)
    out = {}
    for lang, d in load_dicts().items():
        if lang not in NON_SPACE_LANGS:
            continue
        score, hits, cover = 0.0, 0, 0
        for entry, freq in d.items():
            if entry in low:
                score += _w(freq); hits += 1; cover += len(entry)
        if hits:
            out[lang] = (score, hits, cover)
    return out, ns_chars


def _ranked(scores, key=lambda v: v[0]):
    """降序 [(lang, score_value), ...]，score_value 取元组第 0 项并取整便于展示。"""
    items = sorted(scores.items(), key=lambda kv: key(kv[1]), reverse=True)
    return [(l, round(v[0])) for l, v in items]


def detect(text):
    space, n_tokens = _score_space(text)
    non_space, ns_chars = _score_non_space(text)

    space_rank = _ranked(space)
    ns_rank = _ranked(non_space)
    dict_scores = {"space": dict(space_rank), "non_space": dict(ns_rank)}

    # 各路取 top，并算出统一标尺的“覆盖率”
    cands = []  # (lang, coverage, group, score, hits, runner_score)
    if space:
        l, (s, h) = max(space.items(), key=lambda kv: kv[1][0])
        runner = sorted((v[0] for k, v in space.items() if k != l), reverse=True)
        cov = h / max(n_tokens, 1)
        cands.append((l, cov, "space", s, h, runner[0] if runner else 0.0))
    if non_space:
        l, (s, h, c) = max(non_space.items(), key=lambda kv: kv[1][0])
        runner = sorted((v[0] for k, v in non_space.items() if k != l), reverse=True)
        cov = c / max(ns_chars, 1)
        cands.append((l, cov, "non_space", s, h, runner[0] if runner else 0.0))

    if not cands:
        return None

    cands.sort(key=lambda x: x[1], reverse=True)        # 按覆盖率排序
    lang, cov, group, score, hits, runner = cands[0]

    # —— 综合判断的“确定性”检查，任一不满足 -> None（交给后续/模型）——
    if hits < MIN_DICT_HITS:
        return None
    if cov < MIN_DICT_COVERAGE:
        return None
    if runner > 0 and score < runner * DICT_MARGIN:     # 组内次高太接近
        return None
    if len(cands) > 1 and cands[1][0] != lang and cands[1][1] >= cov * 0.8:
        return None                                     # 两路势均力敌（强混合）

    conf = round(min(0.9, max(HIGH_CONF, cov + 0.3)), 4)
    return {"lang": lang, "confidence": conf, "detect_type": "dict",
            "method": "dict:" + group, "dict_scores": dict_scores,
            "note": "词表(%s)命中%d，覆盖率%.0f%%；space=%s non_space=%s" % (
                group, hits, cov * 100, dict(space_rank), dict(ns_rank))}
