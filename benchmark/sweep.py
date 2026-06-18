# -*- coding: utf-8 -*-
"""阈值调参：把某个 config 阈值（环境变量）扫一遍，看各取值下的准确率，找最优。

因为各阈值在模块 import 时绑定，用子进程 + 环境变量重跑 evaluate 才能生效。

用法：
    python benchmark/sweep.py TRAD_RATIO 0.1 0.15 0.2 0.25
    python benchmark/sweep.py RECONCILE_CONF 0.5 0.6 0.65 0.7 0.8
    python benchmark/sweep.py MIN_DICT_COVERAGE 0.1 0.15 0.2 --tag core
"""

import argparse
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_EVAL = os.path.join(_HERE, "evaluate.py")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("var", help="要扫的 config 环境变量名，如 TRAD_RATIO")
    ap.add_argument("values", nargs="+", help="一组取值")
    ap.add_argument("--tag", default=None)
    args = ap.parse_args()

    print("扫描 %s：" % args.var)
    results = []
    for v in args.values:
        env = os.environ.copy()
        env[args.var] = v
        cmd = [sys.executable, _EVAL, "--quiet"]
        if args.tag:
            cmd += ["--tag", args.tag]
        try:
            out = subprocess.check_output(cmd, env=env, stderr=subprocess.STDOUT)
            acc = float(out.decode().strip().splitlines()[-1])
        except Exception as e:
            print("  %s=%s -> 失败: %s" % (args.var, v, e))
            continue
        results.append((v, acc))
        print("  %s=%-8s 准确率 %.4f" % (args.var, v, acc))

    if results:
        best = max(results, key=lambda kv: kv[1])
        print("最优：%s=%s 准确率 %.4f" % (args.var, best[0], best[1]))


if __name__ == "__main__":
    main()
