# 开发计划 / 升级路线（dev.md）

目标：把当前语种检测原型升级为支撑**华为翻译页面**的大型生产服务。

> 检测逻辑本身（强干预 → 词表 → 规则 → 模型 + 分块投票）已较完整。
> 主要缺口在 **工程化、性能、可观测、数据闭环**。下面按优先级列出，并标注当前代码位置与改法。

---

## P0 — 上生产前必须做

### 1. 换掉 Flask 开发服务器
- **现状**：[app.py](app.py) 用 `app.run(debug=True)`，单进程、调试模式，不可上线。
- **改法**：迁 `gunicorn`/`uvicorn` 多 worker，或迁 FastAPI（自带异步、pydantic 校验、OpenAPI 文档）。启动时**预热加载模型**，避免首请求触发懒加载+下载。

### 2. 全局懒加载缓存的线程安全
- **现状**：`_MODEL`(detector)、`_TERMS`(intervene)、`_DICTS`(dict_vote)、`_OPENCC`、`TRAD_UNIQUE` 均为模块级懒加载，多 worker/多线程并发首次访问有竞态。
- **改法**：启动时显式预加载，或加 `threading.Lock`。

### 3. 输入治理 ✅ 已完成
- [x] 最大长度截断（`MAX_INPUT_LEN`），空/超大输入保护。
- [x] **Unicode 归一化(NFKC) + 全半角统一**（[normalize.py](normalize.py) `normalize_text`）。
- [x] 剥离 URL / email / @提及 / emoji / markdown（`[text](url)` 保留文字）。
- [x] 折叠多余空白；`detect(sanitize=True)` 默认开启，页面有开关。
- 待办：请求级超时（属服务层，随 P0#1 一起做）。

### 4. 词库热更新 + 规模化 ✅ 部分完成
- [x] 术语库/词表按 `RESOURCE_RELOAD_TTL`(默认300s) 自动重载；`load_terms/load_dicts(force=True)`。
- [x] 立即重载：`pipeline.reload_all()` + `POST /api/reload`，无需重启。
- 待办（规模化）：TTL 边界重载是同步的，会有单次延迟尖峰 → 改后台线程刷新；
  大规模(百万级术语)避免全量进内存 → Redis 缓存 / 增量加载。

---

## P1 — 性能与准确率（华为级 QPS / 质量）

### 5. 多模式匹配换 Aho-Corasick
- **现状**：[dict_vote.py](dict_vote.py) 非空格子串匹配、[intervene.py](intervene.py) contains 匹配都是 `for entry: if entry in text`，**O(词库×文本)**，最大性能瓶颈。
- **改法**：用 `pyahocorasick` 一次扫描匹配所有词条，O(文本)。

### 6. 结果缓存
- 翻译页面同段文本反复检测。
- **改法**：对 `detect()` 加 LRU/Redis 缓存（key = 归一化文本 + 配置版本）。

### 7. 减少重复计算 + 批量
- **现状**：`script_counts` 在 `detect_one` 和 `rules.features` 各算一次；chunk 投票逐块串行调模型。
- **改法**：features 算一次贯穿全程；chunk 用 fasttext **batch predict**；考虑用 `.bin`（比 `.ftz` 快，换内存）。

### 8. 建评测基准（最重要的质量基建）
- **现状**：仅 76 条单测，**无带标注语料的准确率基准**；阈值(`TRAD_RATIO`/`JA_RATIO`/`LATIN_EN_FALLBACK_CONF`…)全靠手调。
- **改法**：搭每语种标注测试集 + 指标（准确率、per-language F1、混淆矩阵），**数据驱动调阈值**并做回归门禁。短文本(<10字)单独评测，必要时引入专门的 n-gram/小模型。

### 9. 语言代码对齐 BCP-47 + 翻译引擎支持集
- **现状**：输出 `zh`/`zh-Hant`。
- **改法**：对齐翻译引擎语言集（`zh-Hans`/`zh-Hant`/`zh-HK`/`zh-TW` 等）；检测出引擎不支持的语种要有映射/兜底；港台繁体可进一步分 `zh-HK`/`zh-TW`。

---

## P2 — 架构 / 可观测 / 工程化

### 10. 库与服务分离 + 打包
- 核心检测做成可复用 library（`pyproject.toml`、版本化、依赖钉死），HTTP 层独立。
- 规则接口形式化（优先级、可配置开关）。

### 11. 可观测性 + 数据闭环
- 结构化日志 + trace id。
- 指标：P50/P99 延迟、各 `detect_type` 占比、模型兜底率、各语种分布、置信度分布、错误率（Prometheus/Grafana）。
- **低置信/不确定样本采样落库**，喂回评测集和词库迭代，形成正循环。

### 12. 配置与可复现
- env var 迁分层配置（默认+文件+env）+ pydantic 校验。
- **ruleset 与模型打版本号**，结果带 `engine_version`，保证可复现与灰度对比。

### 13. 部署与弹性
- Docker 化 + k8s 水平扩容；服务无状态（词库/模型外置共享存储）。
- 模型 artifact 版本化 + 校验和；按 QPS 自动扩缩。

### 14. 安全合规（华为重点）
- 用户文本含 PII，**默认不落原文日志**；数据保留策略符合 PIPL/GDPR。
- API 鉴权 + 限流。

### 15. API 设计面向翻译页面
- **批量检测**接口（一次多段）。
- 返回 top-N 候选 + 置信度（翻译页可能要备选）。
- 长文档流式；提供「源语 == 目标语」判断。

### 16. CI/CD
- lint + mypy + 覆盖率 + 准确率回归 + 负载测试（locust）。
- 阈值/模型变更走 A/B。

---

## 建议落地顺序

1. **评测基准框架**（标注集 + 准确率/混淆矩阵脚本）—— 没有它，后续所有优化无法验证好坏。
2. **P0 服务化**（gunicorn + 预热 + 线程安全 + 输入治理）。
3. **P1 性能三件套**（Aho-Corasick、缓存、batch）。
4. **可观测 + 数据闭环**，进入「线上低置信样本 → 迭代词库/阈值」的正循环。

---

## 对标谷歌后新增并已完成的优化

- [x] **集成可选 CLD3**（`detector.py`）：装了 `gcld3`/`pycld3` 自动与 fasttext 集成投票，未装优雅降级。
- [x] **可靠性标志**：所有结果带 `reliable`（非自然语言默认/低置信模型/und 为 false）。
- [x] **多语种占比**：结果带 `languages:[{lang,proportion}]`（混合长文取分块投票分布）。
- [x] **去 HTML**（`normalize.strip_html`）：删 script/style/标签 + 反转义实体。
- [x] **始终返回 candidates**：规则/词表/干预路径也补候选。
- [x] **模型自包含**：`download_model()` 显式下载 + 体积校验；`warmup()` 启动预热；服务导入时预热。

### 已知限制 / 待办
- **罗马化/转写文本**（Hinglish 罗马字印地语、阿拉伯聊天字母等）：当前会被 `reconcile` 判成 en。
  谷歌对常见罗马化有处理。短期方案：针对高频场景加专用词表；长期：训练/引入支持罗马化的 LID。
- **集成权重未调**：fasttext 与 CLD3 现等权合并；应在标注集上调权重/做置信度校准。
- **同脚本细分**（fr↔ca、ru↔bg、id↔ms）仍依赖模型 —— 需评测基准 + 更强模型。

## 进度跟踪

| 项 | 优先级 | 状态 | 负责人 | 备注 |
|----|--------|------|--------|------|
| 1. 生产 WSGI/ASGI 服务器 | P0 | TODO | | |
| 2. 缓存线程安全 | P0 | TODO | | |
| 3. 输入治理/归一化 | P0 | ✅ 完成 | | normalize.py，超时待服务层 |
| 4. 词库热更新/规模化 | P0 | 🔶 部分 | | TTL+手动重载已做；后台刷新/Redis 待办 |
| 5. Aho-Corasick 匹配 | P1 | TODO | | |
| 6. 结果缓存 | P1 | TODO | | |
| 7. 去重计算 + batch | P1 | TODO | | |
| 8. 评测基准 | P1 | ✅ 完成 | | benchmark/：标注集+evaluate+sweep+回归门禁 |
| 9. BCP-47 代码对齐 | P1 | TODO | | |
| 10. 库/服务分离 + 打包 | P2 | TODO | | |
| 11. 可观测 + 数据闭环 | P2 | TODO | | |
| 12. 配置版本化 | P2 | TODO | | |
| 13. 容器化/弹性部署 | P2 | TODO | | |
| 14. 安全合规 | P2 | TODO | | |
| 15. 翻译页面 API | P2 | TODO | | |
| 16. CI/CD | P2 | TODO | | |
