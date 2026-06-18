# 评测基准 benchmark

数据驱动地衡量检测质量、调阈值、做回归门禁。

## 文件
- `data/labeled.jsonl` — 标注集，每行 `{"text": "...", "lang": "zh", "tags": ["core"]}`。
  标签：`core`(常规句) / `short`(短文本) / `badcase`(url/数字/乱码/emoji)。
- `evaluate.py` — 评测：总准确率 / 每语种 P-R-F1 / 混淆矩阵 / 按 detect_type 与 reliable 分解 / 误判清单。
- `sweep.py` — 把某个 config 阈值扫一遍找最优。

## 用法
```bash
python benchmark/evaluate.py                       # 完整报告
python benchmark/evaluate.py --tag core            # 只评子集
python benchmark/evaluate.py --min-accuracy 0.9    # 低于则退出码=1（CI 门禁）

python benchmark/sweep.py TRAD_RATIO 0.1 0.15 0.2 0.25
python benchmark/sweep.py RECONCILE_CONF 0.5 0.6 0.7 0.8
```

## 扩充数据集
直接往 `data/labeled.jsonl` 追加行即可（建议每语种 ≥ 20 条、覆盖真实业务文本）。
线上低置信/`reliable=false` 的样本人工标注后回灌这里，形成「数据闭环」。

## 当前发现（示例）
- `TRAD_RATIO=0.15` 优于默认 `0.2`（修复繁体占比恰好 0.2 的边界漏判）。
- 英文停用词规则会被西/法等共享虚词（如 "a"）误触发 —— 需更具区分度的停用词或提高阈值。
- 品牌代号类乱码偶尔被模型高置信误判 —— 依赖 CLD3 集成 / 更强模型。
