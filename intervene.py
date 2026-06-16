# -*- coding: utf-8 -*-
"""第一步：强干预（术语库）。

来源两处，合并使用：
  1. 本地文件 resources/intervene_data/<lang>.txt —— 每行一个术语/字符串。
  2. MySQL 术语库 —— config.MYSQL（enabled=True 时加载，否则跳过）。

匹配逻辑（强干预 = 命中即强制返回该语种）：
  - 整串精确命中：文本(去空白)恰好等于某术语 -> 该语种，置信度极高。
  - 子串命中：文本包含某语种的术语 -> 按命中“覆盖字符数”最多的语种返回。
返回 {lang, confidence, detect_type:'intervene', method, note} 或 None。
"""

import glob
import os

from config import INTERVENE_DIR, MYSQL

# {lang: set(terms)}；懒加载并缓存
_TERMS = None


def _load_local():
    data = {}
    if not os.path.isdir(INTERVENE_DIR):
        return data
    for path in glob.glob(os.path.join(INTERVENE_DIR, "*.txt")):
        lang = os.path.splitext(os.path.basename(path))[0]
        terms = set()
        with open(path, encoding="utf-8") as f:
            for line in f:
                t = line.strip()
                if t and not t.startswith("#"):
                    terms.add(t)
        if terms:
            data.setdefault(lang, set()).update(terms)
    return data


def _load_mysql():
    data = {}
    if not MYSQL.get("enabled"):
        return data
    try:
        import pymysql
        conn = pymysql.connect(
            host=MYSQL["host"], port=MYSQL["port"], user=MYSQL["user"],
            password=MYSQL["password"], database=MYSQL["db"],
            charset=MYSQL["charset"], connect_timeout=5,
        )
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT `%s`, `%s` FROM `%s`"
                            % (MYSQL["term_col"], MYSQL["lang_col"], MYSQL["table"]))
                for term, lang in cur.fetchall():
                    if term and lang:
                        data.setdefault(str(lang), set()).add(str(term).strip())
        finally:
            conn.close()
    except Exception as e:
        # MySQL 不可用不应让整个检测挂掉，降级为只用本地
        print("[intervene] MySQL 加载失败，已跳过：%s" % e)
    return data


def load_terms(force=False):
    """加载并缓存术语库（本地 + MySQL 合并）。"""
    global _TERMS
    if _TERMS is None or force:
        merged = _load_local()
        for lang, terms in _load_mysql().items():
            merged.setdefault(lang, set()).update(terms)
        _TERMS = merged
    return _TERMS


def detect(text):
    terms = load_terms()
    if not terms:
        return None
    stripped = text.strip()

    # 1) 整串精确命中
    for lang, ts in terms.items():
        if stripped in ts:
            return {"lang": lang, "confidence": 0.99,
                    "detect_type": "intervene", "method": "intervene:exact",
                    "note": "整串命中术语库"}

    # 2) 子串命中：按命中术语覆盖的字符数选最强语种
    low = text.lower()
    best_lang, best_cover, best_n = None, 0, 0
    for lang, ts in terms.items():
        cover, n = 0, 0
        for t in ts:
            if t and t.lower() in low:
                cover += len(t)
                n += 1
        if cover > best_cover:
            best_lang, best_cover, best_n = lang, cover, n

    if best_lang is not None:
        return {"lang": best_lang, "confidence": 0.95,
                "detect_type": "intervene", "method": "intervene:contains",
                "note": "命中术语库 %d 条（覆盖%d字符）" % (best_n, best_cover)}
    return None
