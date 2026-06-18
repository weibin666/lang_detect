# -*- coding: utf-8 -*-
"""规则层共享工具：Unicode 脚本统计、简繁/俄乌特征字、英文停用词，以及
为各规则脚本预计算一份 features，避免重复计算。"""

import re

# ---------------------------------------------------------------------------
# 脚本（Unicode block）统计
# ---------------------------------------------------------------------------
def script_of(cp):
    if 0x3040 <= cp <= 0x309F:                            return "hiragana"
    if 0x30A0 <= cp <= 0x30FF or 0x31F0 <= cp <= 0x31FF:  return "katakana"
    if (0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF
            or 0xF900 <= cp <= 0xFAFF or 0x20000 <= cp <= 0x2A6DF): return "han"
    if 0xAC00 <= cp <= 0xD7A3 or 0x1100 <= cp <= 0x11FF:  return "hangul"
    if 0x0400 <= cp <= 0x04FF:                            return "cyrillic"
    if (0x41 <= cp <= 0x5A or 0x61 <= cp <= 0x7A
            or 0x00C0 <= cp <= 0x024F):                   return "latin"
    if 0x0600 <= cp <= 0x06FF or 0x0750 <= cp <= 0x077F:  return "arabic"
    if 0x0590 <= cp <= 0x05FF:                            return "hebrew"
    if 0x0E00 <= cp <= 0x0E7F:                            return "thai"
    if 0x0900 <= cp <= 0x097F:                            return "devanagari"
    if 0x0370 <= cp <= 0x03FF:                            return "greek"
    return None


def script_counts(text):
    counts = {}
    for ch in text:
        s = script_of(ord(ch))
        if s:
            counts[s] = counts.get(s, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# 简体 / 繁体 特征字（常用高频差异字，覆盖典型文本即可）
# ---------------------------------------------------------------------------
_TRAD_CHARS = set(
    "們個這國來時會說對學經發當樣種實頭題問關單務動歷萬與專業東絲兩嚴喪臨為麗舉麼義烏"
    "樂喬習鄉書買亂爭於虧雲亞產畝親億僅從倉儀價眾優傳傷倫偽體餘傭後廠縣參雙嘆嗎員啟園圍"
    "圖團場壞壓壯聲殼賣夢夾奪奮妝婦媽嬰寧寶寵審尋導將爾塵嶺嶼帥師帳帶幣廣莊慶廢開異棄張"
    "彈強歸錄徹徵憂懷態總惡悶慣願懲應憐懶戰戶撲執擴掃揚擾撫拋護報擔擬擁擇掛掙擠換據損擺"
    "攜攝敵數齋斷舊晝術機殺雜權條楊極構槍楓櫃檔橋檢樓標樞樹樣樁歡歐殲殘毀畢氈氣氫匯漢溝"
    "沒淪淚瀉潑澤潔灑漿濟瀏渾濃塗湧濤澇漲澀淵漸漁滲溫灣濕潰濺滿滾濾濫濱觀規覺視覽親譯計"
    "訂認討訓記訪設許訴診詞詢試詩誠話誰課誼調談請論諾謀謝謹識譜證讚讓"
)
_SIMP_CHARS = set(
    "们个这国来时会说对学经发当样种实头题问关单务动历万与专业东丝两严丧临为丽举么义乌"
    "乐乔习乡书买乱争于亏云亚产亩亲亿仅从仓仪价众优传伤伦伪体余佣后厂县参双叹吗员启园围"
    "图团场坏压壮声壳卖梦夹夺奋妆妇妈婴宁宝宠审寻导将尔尘岭屿帅师帐带币广庄庆废开异弃张"
    "弹强归录彻征忧怀态总恶闷惯愿惩应怜懒战户扑执扩扫扬扰抚抛护报担拟拥择挂挣挤换据损摆"
    "携摄敌数斋断旧昼术机杀杂权条杨极构枪枫柜档桥检楼标枢树样桩欢欧歼残毁毕毡气氢汇汉沟"
    "没沦泪泻泼泽洁洒浆济浏浑浓涂涌涛涝涨涩渊渐渔渗温湾湿溃溅满滚滤滥滨观规觉视览亲译计"
    "订认讨训记访设许诉诊词询试诗诚话谁课谊调谈请论诺谋谢谨识谱证赞让"
)

_OPENCC = {}


def opencc_available():
    try:
        import opencc  # noqa: F401
        return True
    except Exception:
        return False


def _opencc(config):
    if config not in _OPENCC:
        import opencc
        _OPENCC[config] = opencc.OpenCC(config)
    return _OPENCC[config]


def _zh_variant_opencc(text):
    to_simp = _opencc("t2s").convert(text)
    to_trad = _opencc("s2t").convert(text)
    trad_signal = sum(1 for a, b in zip(text, to_simp) if a != b)
    simp_signal = sum(1 for a, b in zip(text, to_trad) if a != b)
    lang = "zh-Hant" if trad_signal > simp_signal else "zh"
    return lang, trad_signal, simp_signal


def zh_variant(text, use_opencc=None):
    """判简繁，返回 (lang, trad_signal, simp_signal)。装了 OpenCC 默认用它，否则特征字法。"""
    if use_opencc is None:
        use_opencc = opencc_available()
    if use_opencc:
        try:
            return _zh_variant_opencc(text)
        except Exception:
            pass
    trad = sum(1 for c in text if c in _TRAD_CHARS)
    simp = sum(1 for c in text if c in _SIMP_CHARS)
    lang = "zh-Hant" if trad > simp else "zh"
    return lang, trad, simp


# ---------------------------------------------------------------------------
# 繁体独有 / 简体独有 字符集（用于占比强规则）
#   - 繁体独有：不与简体共享的字（香港/台湾繁体通用，二者繁体字集基本一致）。
#   - 简体独有：不与繁体共享的字。
# 优先用 OpenCC 全量生成（覆盖最全）：
#   某字经 t2s 会变 -> 它是“繁体形”，属繁体独有；
#   某字经 s2t 会变 -> 它是“简体形”，属简体独有。
# 没装 OpenCC 时退回内置特征字表（_TRAD_CHARS / _SIMP_CHARS）。
# ---------------------------------------------------------------------------
def _gen_variant_sets():
    if opencc_available():
        try:
            chars = "".join(chr(c) for c in range(0x4E00, 0x9FFF + 1))
            to_simp = _opencc("t2s").convert(chars)
            to_trad = _opencc("s2t").convert(chars)
            trad_unique = {h for h, s in zip(chars, to_simp) if h != s}
            simp_unique = {h for h, t in zip(chars, to_trad) if h != t}
            if trad_unique and simp_unique:
                return trad_unique, simp_unique
        except Exception:
            pass
    return set(_TRAD_CHARS), set(_SIMP_CHARS)


TRAD_UNIQUE, SIMP_UNIQUE = _gen_variant_sets()

# ---------------------------------------------------------------------------
# 日语独有汉字（和製漢字 kokuji + 新字体 shinjitai），不与简体/繁体共享。
# 假名(平假名/片假名)本身就是日语独有，单独按 Unicode 区间统计，不放这里。
# 这里只列“高置信、确定不是中文（简/繁）”的汉字，避免误判中文。
# ---------------------------------------------------------------------------
JP_UNIQUE_KANJI = set(
    "働込畑峠辻匂枠塀凪笹雫躾栃麿俣偲凧喰噺樫畠"      # 和製漢字 kokuji
    "円図売読駅営観圧価児剣検権楽歓縄説黒歩巻巣帯徳応恵悩戸抜"  # 新字体 shinjitai(与简繁均不同)
    "気駆鉄広転済薬覚厳"                          # 其他常见新字体
)
# 严格保证“日语独有”：剔除与简/繁中文共享(被 OpenCC 认作可转换)的字
JP_UNIQUE_KANJI -= (TRAD_UNIQUE | SIMP_UNIQUE)


# ---------------------------------------------------------------------------
# 俄语 / 乌克兰语 特征字母
#   乌克兰语独有: і ї є ґ      俄语独有: ы э ъ ё
# ---------------------------------------------------------------------------
_UK_ONLY = set("іїєґ")
_RU_ONLY = set("ыэъё")


def cyrillic_ru_uk(text):
    """返回 (lang, uk_hits, ru_hits)。都没有特征字母时默认 ru。"""
    low = text.lower()
    uk = sum(1 for c in low if c in _UK_ONLY)
    ru = sum(1 for c in low if c in _RU_ONLY)
    lang = "uk" if uk > ru else "ru"
    return lang, uk, ru


# ---------------------------------------------------------------------------
# 英文停用词
# ---------------------------------------------------------------------------
_EN_STOPWORDS = set(
    "the be to of and a in that have i it for not on with he as you do at this but his by "
    "from they we say her she or an will my one all would there their what so up out if about "
    "who get which go me when make can like time no just him know take people into year your "
    "good some could them see other than then now look only come its over think also back "
    "after use two how our work first well way even new want because any these give day most us "
    "is are was were am been being has had did does".split()
)


def looks_english(text):
    """返回 (is_en, ratio)。

    需命中 >= 2 个**不同**英文停用词：避免被西/法等共享虚词（如 "a"）误触发——
    例 "voy a visitar a mis padres" 只命中 "a"(1个不同词)，不应判英文。
    """
    # 用 Unicode 词正则，避免把 "días" 切成 "d"+"as"（"as" 恰是英文停用词造成误判）
    words = re.findall(r"[^\W\d_]+", text.lower(), re.UNICODE)
    if not words:
        return False, 0.0
    matched = {w for w in words if w in _EN_STOPWORDS}
    hits = sum(1 for w in words if w in _EN_STOPWORDS)
    ratio = hits / len(words)
    # 需 >=2 个不同停用词 且 占比 >=0.25，避免西/法等共享虚词(a/he/me)误判英文
    return (len(words) >= 2 and len(matched) >= 2 and ratio >= 0.25), ratio


# 中文营销文案里常被借用的少量假名（の 之类），不据此判日语
BORROWED_KANA = set("の・")


# ---------------------------------------------------------------------------
# 为规则脚本预计算 features（只算一次，传给每个规则脚本）
# ---------------------------------------------------------------------------
def features(text, use_opencc=None):
    counts = script_counts(text)
    hira = counts.get("hiragana", 0)
    kata = counts.get("katakana", 0)
    kana = hira + kata
    han = counts.get("han", 0)
    cyr = counts.get("cyrillic", 0)
    latin = counts.get("latin", 0)
    hangul = counts.get("hangul", 0)
    total = sum(counts.values())

    # 假名细节（区分真假名 / 借用假名）
    kana_set = set(c for c in text if script_of(ord(c)) in ("hiragana", "katakana"))
    genuine_kana = kana_set - BORROWED_KANA

    # 繁体独有 / 简体独有 / 日语独有汉字 计数
    trad_unique = sum(1 for c in text if c in TRAD_UNIQUE)
    simp_unique = sum(1 for c in text if c in SIMP_UNIQUE)
    jp_kanji = sum(1 for c in text if c in JP_UNIQUE_KANJI)

    cjk = han + kana
    # 占比：繁体按汉字数为分母；日语(假名+和製漢字)按 CJK(汉字+假名)为分母
    trad_ratio = trad_unique / han if han else 0.0
    simp_ratio = simp_unique / han if han else 0.0
    ja_ratio = (kana + jp_kanji) / cjk if cjk else 0.0

    uk_hits = sum(1 for c in text.lower() if c in _UK_ONLY)
    ru_hits = sum(1 for c in text.lower() if c in _RU_ONLY)

    dominant = max(counts, key=counts.get) if counts else None

    return {
        "text": text,
        "counts": counts, "total": total, "dominant": dominant,
        "hira": hira, "kata": kata, "kana": kana, "cjk": cjk,
        "kana_genuine": bool(genuine_kana),
        "han": han, "cyr": cyr, "latin": latin, "hangul": hangul,
        "trad_unique": trad_unique, "simp_unique": simp_unique, "jp_kanji": jp_kanji,
        "trad_ratio": trad_ratio, "simp_ratio": simp_ratio, "ja_ratio": ja_ratio,
        "uk_hits": uk_hits, "ru_hits": ru_hits,
    }
