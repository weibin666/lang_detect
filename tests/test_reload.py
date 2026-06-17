# -*- coding: utf-8 -*-
"""词库 / 词表 热更新测试。"""
import os

import dict_vote
import intervene
import pipeline
from config import DICT_DIR, INTERVENE_DIR


def test_reload_terms_returns_counts():
    counts = intervene.reload_terms()
    assert isinstance(counts, dict)
    assert counts.get("zh", 0) >= 1


def test_reload_dicts_returns_counts():
    counts = dict_vote.reload_dicts()
    assert isinstance(counts, dict)
    assert counts.get("en", 0) >= 1


def test_reload_all_structure():
    out = pipeline.reload_all()
    assert set(out.keys()) == {"intervene", "dict"}


def test_hot_reload_picks_up_new_term_file():
    """新增一个术语文件 -> reload 后应被加载（验证热更新真生效）。"""
    path = os.path.join(INTERVENE_DIR, "zz_test.txt")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("特殊测试术语ZZ\n")
        counts = intervene.reload_terms()
        assert counts.get("zz_test", 0) == 1
        r = intervene.detect("这里包含特殊测试术语ZZ的文本")
        assert r is not None and r["lang"] == "zz_test"
    finally:
        if os.path.exists(path):
            os.remove(path)
        intervene.reload_terms()   # 复原缓存


def test_hot_reload_picks_up_new_dict_file():
    path = os.path.join(DICT_DIR, "zz.csv")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("zzfoo,500\nzzbar,400\n")
        counts = dict_vote.reload_dicts()
        assert counts.get("zz", 0) == 2
    finally:
        if os.path.exists(path):
            os.remove(path)
        dict_vote.reload_dicts()
