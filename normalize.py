# -*- coding: utf-8 -*-
"""输入治理：检测前对文本做清洗与归一化。

步骤（sanitize 一次性完成）：
  1. 截断超长（MAX_INPUT_LEN）防滥用/DoS。
  2. 去噪：URL、email、@提及、emoji、markdown 标记（#、*、_、~、`、>、图片/链接语法）。
     —— 这些对语种无意义，会污染检测。#标签/[]()链接保留其中文字。
  3. Unicode 归一化 NFKC + 全/半角统一（全角字母数字→半角，半角片假名→全角等）。
  4. 折叠多余空白。

只清洗、不判定语种。返回清洗后的文本。
"""

import re
import unicodedata

from config import MAX_INPUT_LEN

_URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_MENTION_RE = re.compile(r"@\w+")
_MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")          # ![alt](url) -> 删
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")          # [text](url) -> text
_MD_MARKERS_RE = re.compile(r"[#*_~`>|]+")                  # markdown/标签 标记符
_WS_RE = re.compile(r"\s+")

# 常见 emoji / 符号区段（变体选择符、ZWJ、区域指示符等）
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"   # 各类 emoji / 符号 / 补充
    "\U0001F000-\U0001F0FF"   # 麻将/多米诺/扑克
    "\U00002600-\U000027BF"   # 杂项符号 + Dingbats
    "\U00002B00-\U00002BFF"   # 杂项符号箭头
    "\U0001F1E6-\U0001F1FF"   # 区域指示符（国旗）
    "\U0000FE00-\U0000FE0F"   # 变体选择符
    "\U0000200D"              # 零宽连接符 ZWJ
    "\U00002022"              # bullet •
    "]",
    flags=re.UNICODE,
)


def strip_noise(text):
    """去掉 URL / email / @提及 / emoji / markdown 标记。

    顺序要点：先处理 markdown 图片/链接（保留链接文字），再删 URL，
    否则 URL 正则会把链接里的地址先吃掉、破坏 [text](url) 结构。
    """
    text = _MD_IMAGE_RE.sub(" ", text)     # ![alt](url) -> 删
    text = _MD_LINK_RE.sub(r"\1", text)    # [text](url) -> text（须在删URL前）
    text = _URL_RE.sub(" ", text)
    text = _EMAIL_RE.sub(" ", text)
    text = _MENTION_RE.sub(" ", text)
    text = _EMOJI_RE.sub("", text)
    text = _MD_MARKERS_RE.sub(" ", text)
    return text


def normalize_text(text):
    """Unicode NFKC 归一化（含全/半角统一）。"""
    return unicodedata.normalize("NFKC", text)


def sanitize(text, max_len=None):
    """完整输入治理：截断 -> 去噪 -> NFKC 归一化 -> 折叠空白。"""
    if not text:
        return ""
    if max_len is None:
        max_len = MAX_INPUT_LEN
    if max_len and len(text) > max_len:
        text = text[:max_len]
    text = strip_noise(text)
    text = normalize_text(text)
    text = _WS_RE.sub(" ", text).strip()
    return text
