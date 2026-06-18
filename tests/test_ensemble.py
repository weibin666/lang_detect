# -*- coding: utf-8 -*-
"""fasttext (+可选 CLD3) 集成预测测试。"""
from detector import _merge_predictions, cld3_available, ensemble_predict


def test_merge_weighted_normalized():
    ft = [("en", 0.6), ("de", 0.3), ("fr", 0.1)]
    c3 = [("en", 0.8), ("nl", 0.2)]
    merged = _merge_predictions(ft, c3)
    assert merged[0][0] == "en"                       # 两模型都偏 en
    assert abs(sum(s for _, s in merged) - 1.0) < 1e-6  # 归一化
    assert dict(merged).keys() >= {"en", "de", "fr", "nl"}


def test_merge_empty_c3():
    ft = [("zh", 0.9), ("ja", 0.1)]
    merged = _merge_predictions(ft, None)
    assert merged[0][0] == "zh"


def test_ensemble_graceful_without_cld3():
    cands, used = ensemble_predict("this is a clear english sentence here")
    assert cands and cands[0][0] == "en"
    if cld3_available():
        assert "cld3" in used
    else:
        assert used == ["fasttext"]
