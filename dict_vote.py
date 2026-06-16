# -*- coding: utf-8 -*-
"""第二步：词表判断。

每个语种一个 CSV：resources/dict/<lang>.csv，每行 `词,词频`（也兼容空格/制表分隔）。
例：
    hello,100
    你好,1200

打分：把文本里命中的词，按 log(1+词频) 累加成该语种得分；
取最高分语种，需满足：命中条目数 >= MIN_DICT_HITS，且 最高分 >= 次高分 * DICT_MARGIN，
才采纳词表结果（否则返回 None，交给规则层）。

匹配方式：
  - ASCII 单词条目（如 hello）：按分词后的“整词命中”。
  - 其他（中日韩等无空格 / 短语）：按子串包含命中。
"""

import csv
import glob
import math
import os
import re

from config import DICT_DIR, DICT_MARGIN, HIGH_CONF, MIN_DICT_HITS

# {lang: {"words": {w: freq}, "subs": [(entry, freq), ...]}}
_DICTS = None
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
_ASCII_WORD = re.compile(r"^[a-z][a-z']*$")


def _parse_row(row):
    """从一行里解析 (word, freq)，兼容逗号/空格/制表分隔。"""
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
    global _DICTS
    if _DICTS is not None and not force:
        return _DICTS
    dicts = {}
    if os.path.isdir(DICT_DIR):
        for path in glob.glob(os.path.join(DICT_DIR, "*.csv")):
            lang = os.path.splitext(os.path.basename(path))[0]
            words, subs = {}, []
            with open(path, encoding="utf-8") as f:
                for row in csv.reader(f):
                    if not row or row[0].lstrip().startswith("#"):
                        continue
                    pr = _parse_row(row)
                    if not pr:
                        continue
                    word, freq = pr
                    if _ASCII_WORD.match(word):
                        words[word] = freq
                    else:
                        subs.append((word, freq))
            if words or subs:
                dicts[lang] = {"words": words, "subs": subs}
    _DICTS = dicts
    return _DICTS


def _score(text):
    """返回 {lang: (score, hit_count)}。"""
    dicts = load_dicts()
    low = text.lower()
    tokens = _WORD_RE.findall(low)
    token_set = set(tokens)
    scores = {}
    for lang, d in dicts.items():
        score, hits = 0.0, 0
        for w in token_set:
            if w in d["words"]:
                score += math.log(1 + d["words"][w])
                hits += 1
        for entry, freq in d["subs"]:
            if entry in low:
                score += math.log(1 + freq)
                hits += 1
        if hits:
            scores[lang] = (score, hits)
    return scores


def detect(text):
    scores = _score(text)
    if not scores:
        return None
    ranked = sorted(scores.items(), key=lambda kv: kv[1][0], reverse=True)
    (lang, (score, hits)) = ranked[0]
    runner = ranked[1][1][0] if len(ranked) > 1 else 0.0

    if hits < MIN_DICT_HITS:
        return None
    if runner > 0 and score < runner * DICT_MARGIN:
        return None  # 与次高分差距不够，判定不可靠

    # 置信度：领先优势 -> 0.6~0.9
    share = score / (score + runner) if (score + runner) else 1.0
    conf = round(min(0.9, max(HIGH_CONF, share)), 4)
    return {"lang": lang, "confidence": conf,
            "detect_type": "dict", "method": "dict:wordlist",
            "note": "词表命中 %d 条，得分 %.2f（次高 %.2f）" % (hits, score, runner)}
