# 语种检测 Language Detection

四层级联的混合语种检测：**强干预 → 词表 → 规则 → 模型兜底**，自带连续重复去重、超长分块投票，附带 Web 页面。每个结果都带 `detect_type` 标明命中来源。

## 检测流程

```
detect(text)
 └─ 预处理：去重 collapse_repeats
 └─ 超长(>1200字符)? → 分块 → 每块 detect_one → 加权投票
    否则 → detect_one 一次

detect_one(text)  —— 顺序执行，第一个命中即返回，并打 detect_type 标签
 1. 强干预 intervene   术语库：MySQL + 本地 resources/intervene_data/<lang>.txt   detect_type=intervene
 2. 词表   dict_vote   resources/dict/<lang>.csv (词,词频) 打分                   detect_type=dict
 3. 规则   rules/*.py  每语种/混合各一个脚本                                       detect_type=rule
      zh_ja_mix · zh_hant_mix · zh_hant · zh · ko · ru_uk_mix · en
 4. 模型   detector    fasttext lid.176 + 低资源级联(custom33 / langid)            detect_type=model
```

返回 dict 关键字段：`lang / confidence / detect_type / method / note / scripts / cleaned_text / chunks`；分块时还有 `votes`（各语种票重与占比）。

## 各层说明

### 1. 强干预（术语库）`intervene.py`
- **本地**：`resources/intervene_data/<lang>.txt`，每行一个术语。
- **MySQL**：`config.MYSQL`，`MYSQL_ENABLED=1` 时加载（表名/列名可配）；连不上自动降级为只用本地，不报错。
- 整串精确命中 → 该语种(0.99)；否则按术语覆盖字符数最多的语种返回(0.95)。

### 2. 词表 `dict_vote.py`
- 每语种 `resources/dict/<lang>.csv`，行格式 `词,词频`（兼容空格/制表分隔）。
- 命中词按 `log(1+词频)` 累加得分；需命中数 `>= MIN_DICT_HITS` 且领先次高 `* DICT_MARGIN` 才采纳，否则交给规则层。

### 3. 规则 `rules/`（模块化，每个语种/混合一个脚本）
- `zh_ja_mix`：含假名 → 日语（区分 zh/ja 的关键；汉字+假名混排判主语种为 ja）。借用假名「の」且占比极低时不判日语。
- `zh_hant_mix`：同时出现简体+繁体特征字 → 简繁混合，按多者返回主语种。
- `zh_hant` / `zh`：纯繁体 / 纯简体。简繁判定走 OpenCC（装了就用）或内置特征字法，开关 `use_opencc`。
- `ko`：谚文。
- `ru_uk_mix`：西里尔按特征字母（乌 `іїєґ` / 俄 `ыэъё`）区分；都没有则交给模型层。
- `en`：拉丁 + 英文停用词占比。

### 4. 模型兜底 `detector.py` + `cascade_models.py`
- fasttext lid.176 覆盖 100+ 语种。
- **ru/uk 易混**：模型 top1/top2 同为 `{ru, uk}` → 混合，用特征字母（无则用模型主候选）返回主语种。
- **低资源级联**：lid.176 top1 置信度 `< LOW_CONF(0.3)` 且语种 ∈ `langs33.txt` 的 33 个 → 走自训 33 语种 fastText 模型（`models/custom33.ftz`）；仍 `< 0.3` 或模型缺失 → langid.py 兜底。

## 超长分块投票
文本去重后若 `> CHUNK_SIZE(1200)`，按 ~1200 字符在空白处分块，每块独立检测，再按 `置信度 × 块字符数` 加权投票得主语种；`votes` 字段给出各语种占比。

## 安装与运行
```bash
pip3 install -r requirements.txt   # 注意 numpy<2，否则 fasttext predict 报错
python3 app.py                     # 打开 http://127.0.0.1:5000
```
首次检测会自动下载 fasttext 模型（约 1MB，存到 `models/lid.176.ftz`）。

## 配置（`config.py`，均可用同名环境变量覆盖）

| 配置 | 默认 | 说明 |
|------|------|------|
| `LID176_PATH` / `LID176_URL` | `models/lid.176.ftz` | 开源兜底模型路径/下载地址 |
| `CUSTOM33_MODEL_PATH` | `models/custom33.ftz` | 自训 33 语种模型 |
| `LANGS33_PATH` | `langs33.txt` | 33 语种代码清单（占位示例，请替换） |
| `LOW_CONF` / `HIGH_CONF` | `0.3` / `0.6` | 级联降级/高置信阈值 |
| `CHUNK_SIZE` | `1200` | 超长分块阈值 |
| `MIN_DICT_HITS` / `DICT_MARGIN` | `2` / `1.3` | 词表采纳阈值 |
| `RESOURCES_DIR` / `INTERVENE_DIR` / `DICT_DIR` | `resources/...` | 资源目录 |
| `MYSQL_*` | 见 config | MySQL 术语库连接（`MYSQL_ENABLED=1` 启用） |
| `DEFAULT_MIN_REPEATS` | `3` | 去重默认阈值 |

例：`MYSQL_ENABLED=1 MYSQL_HOST=db LOW_CONF=0.25 python3 app.py`

## 代码结构
- `config.py` — 统一配置。
- `pipeline.py` — 主编排：四层串联 + 分块投票，对外 `detect(text, ...)`。
- `dedup_repeats.py` — 连续重复折叠。
- `intervene.py` — 强干预层。 `dict_vote.py` — 词表层。
- `rules/` — 规则层：`script_utils.py`(共享) + 各语种/混合脚本 + `__init__.py`(调度)。
- `detector.py` — 模型层 `model_fallback()`。 `cascade_models.py` — 低资源级联。
- `langs33.txt` — 33 语种清单。 `lang_names.py` — 代码→名称。
- `resources/intervene_data/*.txt`、`resources/dict/*.csv` — 干预/词表数据。
- `app.py` + `templates/index.html` — Web 服务与页面。

## 测试
```bash
python3 -m pytest -q   # 覆盖去重 / 四层 / detect_type / 分块投票，共 37 条
```
`tests/` 下按模块拆分：`test_dedup` · `test_rules` · `test_intervene_dict` · `test_pipeline`。
依赖 lid.176 模型的两条用例在模型缺失时自动跳过。

## 直接调用
```python
from pipeline import detect
detect("请用人民币支付")          # -> {'lang':'zh', 'detect_type':'intervene', ...}
detect("我們在臺灣使用繁體中文")   # -> {'lang':'zh-Hant', 'detect_type':'rule', ...}
```
