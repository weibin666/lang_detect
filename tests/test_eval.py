# -*- coding: utf-8 -*-
"""评测基准回归门禁：标注集整体准确率不应跌破阈值。"""
import os

import pytest

from config import LID176_PATH

needs_model = pytest.mark.skipif(not os.path.exists(LID176_PATH),
                                 reason="lid.176 模型未就绪")


@needs_model
def test_benchmark_accuracy_gate():
    from benchmark.evaluate import run_eval
    m = run_eval()
    assert m["n"] >= 50
    assert m["accuracy"] >= 0.90, "总准确率回退到 %.3f" % m["accuracy"]
    assert m["macro_f1"] >= 0.88, "宏F1回退到 %.3f" % m["macro_f1"]


@needs_model
def test_badcase_subset_handled():
    from benchmark.evaluate import run_eval
    m = run_eval(tag="badcase")
    # badcase（url/数字/乱码->en，emoji/标点->und）应基本都对
    assert m["accuracy"] >= 0.75
