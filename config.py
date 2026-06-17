# -*- coding: utf-8 -*-
"""统一配置。所有路径/阈值集中在此，均可用环境变量覆盖。"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.environ.get("MODELS_DIR", os.path.join(BASE_DIR, "models"))


def _path(env, default_name, base=MODELS_DIR):
    return os.environ.get(env, os.path.join(base, default_name))


# --- 开源兜底模型 fasttext lid.176 ---
LID176_PATH = _path("LID176_PATH", "lid.176.ftz")
LID176_URL = os.environ.get(
    "LID176_URL",
    "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz",
)

# --- 自训 33 语种 fasttext 模型 ---
CUSTOM33_MODEL_PATH = _path("CUSTOM33_MODEL_PATH", "custom33.ftz")

# --- 33 语种代码清单（一行一个，支持 # 注释） ---
LANGS33_PATH = os.environ.get("LANGS33_PATH", os.path.join(BASE_DIR, "langs33.txt"))

# --- 级联置信度阈值 ---
LOW_CONF = float(os.environ.get("LOW_CONF", "0.3"))    # 低于它 -> 降级到下一个模型
HIGH_CONF = float(os.environ.get("HIGH_CONF", "0.6"))  # 高于它 -> 高置信

# --- 去重默认参数 ---
DEFAULT_MIN_REPEATS = int(os.environ.get("DEFAULT_MIN_REPEATS", "3"))

# --- 超长文本分块 + 投票 ---
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "1200"))  # 超过则按此长度分块投票

# --- 繁体 / 日语 字符占比阈值（基于“独有字符集”占比的强规则） ---
# 繁体独有字(不与简体共享)占汉字比 > TRAD_RATIO -> zh-Hant
TRAD_RATIO = float(os.environ.get("TRAD_RATIO", "0.2"))
# 日语独有字(假名+和製漢字/新字体，不与简繁共享)占CJK比 > JA_RATIO -> ja
JA_RATIO = float(os.environ.get("JA_RATIO", "0.1"))
# 中英混合：中文字符占(中文+英文)比 > ZH_EN_MIX_RATIO -> zh，否则交给英文规则/模型
ZH_EN_MIX_RATIO = float(os.environ.get("ZH_EN_MIX_RATIO", "0.1"))

# 纯ASCII拉丁(无变音符)且模型置信度低于此值 -> 视为非真实语言的字母串(乱码/代号)，默认 en
# 调高更激进(把更多低置信拉丁判 en)，调低更保守
LATIN_EN_FALLBACK_CONF = float(os.environ.get("LATIN_EN_FALLBACK_CONF", "0.65"))

# --- 资源目录 ---
RESOURCES_DIR = os.environ.get("RESOURCES_DIR", os.path.join(BASE_DIR, "resources"))
INTERVENE_DIR = os.environ.get("INTERVENE_DIR", os.path.join(RESOURCES_DIR, "intervene_data"))
DICT_DIR = os.environ.get("DICT_DIR", os.path.join(RESOURCES_DIR, "dict"))

# 词库/词表热更新：每隔 RESOURCE_RELOAD_TTL 秒检查并重载一次（0=只加载一次不自动重载）。
# 也可调 reload_all() 或 POST /api/reload 立即重载。
RESOURCE_RELOAD_TTL = int(os.environ.get("RESOURCE_RELOAD_TTL", "300"))

# --- 输入治理 ---
MAX_INPUT_LEN = int(os.environ.get("MAX_INPUT_LEN", "100000"))  # 超过则截断，防滥用/DoS

# --- 词表层阈值 ---
# 命中条目数 >= MIN_DICT_HITS 且 主语种得分 >= 次高 * DICT_MARGIN 才采纳词表结果
MIN_DICT_HITS = int(os.environ.get("MIN_DICT_HITS", "2"))
DICT_MARGIN = float(os.environ.get("DICT_MARGIN", "1.3"))
# 主语种“覆盖率”(识别词数/字符数 占比) 需 >= 此值，否则视为不确定 -> 交给后续/模型
MIN_DICT_COVERAGE = float(os.environ.get("MIN_DICT_COVERAGE", "0.15"))

# --- MySQL 术语库（强干预，除本地文件外的来源） ---
# 表结构假设：一张表，至少有 “术语列” 和 “语种列” 两列，可在下方配置列名/表名。
MYSQL = {
    "enabled": os.environ.get("MYSQL_ENABLED", "0") in ("1", "true", "True"),
    "host": os.environ.get("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", ""),
    "db": os.environ.get("MYSQL_DB", "lang_detect"),
    "table": os.environ.get("MYSQL_TABLE", "intervene_terms"),
    "term_col": os.environ.get("MYSQL_TERM_COL", "term"),
    "lang_col": os.environ.get("MYSQL_LANG_COL", "lang"),
    "charset": os.environ.get("MYSQL_CHARSET", "utf8mb4"),
}
