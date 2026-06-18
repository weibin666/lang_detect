# -*- coding: utf-8 -*-
"""语种检测评测：跑标注集，输出准确率 / 每语种 P-R-F1 / 混淆矩阵 /
detect_type 与 reliable 分解。

用法：
    python benchmark/evaluate.py                      # 跑默认标注集
    python benchmark/evaluate.py --tag core           # 只评 core 子集
    python benchmark/evaluate.py --min-accuracy 0.85  # 低于阈值退出码=1（CI 门禁）
    python benchmark/evaluate.py --quiet              # 只打印总准确率（供 sweep 解析）
也可作模块：from benchmark.evaluate import run_eval
"""

import argparse
import collections
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from pipeline import detect  # noqa: E402

DEFAULT_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "labeled.jsonl")


def load_dataset(path, tag=None):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if tag and tag not in row.get("tags", []):
                continue
            rows.append(row)
    return rows


def run_eval(path=DEFAULT_DATA, tag=None):
    rows = load_dataset(path, tag)
    confusion = collections.defaultdict(collections.Counter)   # gold -> Counter(pred)
    n = correct = 0
    by_type = collections.Counter()
    by_type_correct = collections.Counter()
    rel = {"reliable": [0, 0], "unreliable": [0, 0]}           # key -> [correct, total]
    errors = []

    for row in rows:
        res = detect(row["text"])
        gold, pred = row["lang"], res["lang"]
        ok = int(pred == gold)
        confusion[gold][pred] += 1
        n += 1
        correct += ok
        by_type[res["detect_type"]] += 1
        by_type_correct[res["detect_type"]] += ok
        bucket = "reliable" if res.get("reliable") else "unreliable"
        rel[bucket][0] += ok
        rel[bucket][1] += 1
        if not ok:
            errors.append({"text": row["text"][:40], "gold": gold,
                           "pred": pred, "method": res.get("method")})

    langs = sorted(set(confusion) | {p for g in confusion for p in confusion[g]})
    per_lang = {}
    for L in langs:
        tp = confusion[L][L]
        fp = sum(confusion[g][L] for g in confusion if g != L)
        fn = sum(confusion[L][p] for p in confusion[L] if p != L)
        support = sum(confusion[L].values())
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        if support or tp or fp:
            per_lang[L] = {"precision": prec, "recall": rec, "f1": f1, "support": support}

    macro_f1 = sum(d["f1"] for d in per_lang.values() if d["support"]) / \
        max(1, sum(1 for d in per_lang.values() if d["support"]))

    return {
        "n": n,
        "accuracy": correct / n if n else 0.0,
        "macro_f1": macro_f1,
        "per_lang": per_lang,
        "confusion": {g: dict(c) for g, c in confusion.items()},
        "by_type": {t: {"acc": by_type_correct[t] / by_type[t], "n": by_type[t]}
                    for t in by_type},
        "reliability": {k: {"acc": (v[0] / v[1] if v[1] else 0.0), "n": v[1]}
                        for k, v in rel.items()},
        "errors": errors,
    }


def _print_report(m):
    print("=" * 60)
    print("样本数 %d   总准确率 %.3f   宏F1 %.3f" % (m["n"], m["accuracy"], m["macro_f1"]))
    print("-" * 60)
    print("%-9s %8s %8s %8s %8s" % ("lang", "prec", "recall", "f1", "support"))
    for L, d in sorted(m["per_lang"].items(), key=lambda kv: -kv[1]["support"]):
        print("%-9s %8.2f %8.2f %8.2f %8d"
              % (L, d["precision"], d["recall"], d["f1"], d["support"]))
    print("-" * 60)
    print("按 detect_type:")
    for t, d in sorted(m["by_type"].items(), key=lambda kv: -kv[1]["n"]):
        print("  %-12s acc=%.3f  n=%d" % (t, d["acc"], d["n"]))
    print("可靠性校准（reliable 应当更准）:")
    for k, d in m["reliability"].items():
        print("  %-12s acc=%.3f  n=%d" % (k, d["acc"], d["n"]))
    if m["errors"]:
        print("-" * 60)
        print("误判 (%d):" % len(m["errors"]))
        for e in m["errors"]:
            print("  gold=%-7s pred=%-7s [%s] %r" % (e["gold"], e["pred"], e["method"], e["text"]))
    # 混淆矩阵（仅非零）
    print("-" * 60)
    print("混淆矩阵 gold -> {pred: n}（仅错分项标*）:")
    for g in sorted(m["confusion"]):
        cells = ", ".join("%s%s:%d" % ("*" if p != g else "", p, c)
                          for p, c in sorted(m["confusion"][g].items(), key=lambda x: -x[1]))
        print("  %-8s %s" % (g, cells))
    print("=" * 60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=DEFAULT_DATA)
    ap.add_argument("--tag", default=None, help="只评带此标签的子集，如 core/short/badcase")
    ap.add_argument("--min-accuracy", type=float, default=None, help="低于则退出码=1")
    ap.add_argument("--quiet", action="store_true", help="只打印总准确率")
    args = ap.parse_args()

    m = run_eval(args.data, args.tag)
    if args.quiet:
        print("%.6f" % m["accuracy"])
    else:
        _print_report(m)
    if args.min_accuracy is not None and m["accuracy"] < args.min_accuracy:
        print("准确率 %.3f 低于门槛 %.3f" % (m["accuracy"], args.min_accuracy), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
