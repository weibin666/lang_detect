# -*- coding: utf-8 -*-
"""语种代码 -> 中文/英文名称（用于页面展示）。覆盖 fasttext lid.176 的常见代码。"""

LANG_NAMES = {
    "zh": "中文(简体) Chinese", "zh-Hant": "中文(繁体) Chinese (Traditional)",
    "ja": "日语 Japanese", "ko": "韩语 Korean", "en": "英语 English",
    "ru": "俄语 Russian", "uk": "乌克兰语 Ukrainian", "fr": "法语 French",
    "de": "德语 German", "es": "西班牙语 Spanish", "pt": "葡萄牙语 Portuguese",
    "it": "意大利语 Italian", "nl": "荷兰语 Dutch", "pl": "波兰语 Polish",
    "ar": "阿拉伯语 Arabic", "he": "希伯来语 Hebrew", "tr": "土耳其语 Turkish",
    "th": "泰语 Thai", "vi": "越南语 Vietnamese", "id": "印尼语 Indonesian",
    "ms": "马来语 Malay", "hi": "印地语 Hindi", "bn": "孟加拉语 Bengali",
    "fa": "波斯语 Persian", "ur": "乌尔都语 Urdu", "el": "希腊语 Greek",
    "sv": "瑞典语 Swedish", "no": "挪威语 Norwegian", "da": "丹麦语 Danish",
    "fi": "芬兰语 Finnish", "cs": "捷克语 Czech", "sk": "斯洛伐克语 Slovak",
    "hu": "匈牙利语 Hungarian", "ro": "罗马尼亚语 Romanian", "bg": "保加利亚语 Bulgarian",
    "sr": "塞尔维亚语 Serbian", "hr": "克罗地亚语 Croatian", "sl": "斯洛文尼亚语 Slovenian",
    "lt": "立陶宛语 Lithuanian", "lv": "拉脱维亚语 Latvian", "et": "爱沙尼亚语 Estonian",
    "ca": "加泰罗尼亚语 Catalan", "eu": "巴斯克语 Basque", "gl": "加利西亚语 Galician",
    "is": "冰岛语 Icelandic", "ga": "爱尔兰语 Irish", "cy": "威尔士语 Welsh",
    "ta": "泰米尔语 Tamil", "te": "泰卢固语 Telugu", "kn": "卡纳达语 Kannada",
    "ml": "马拉雅拉姆语 Malayalam", "mr": "马拉地语 Marathi", "gu": "古吉拉特语 Gujarati",
    "pa": "旁遮普语 Punjabi", "ne": "尼泊尔语 Nepali", "si": "僧伽罗语 Sinhala",
    "my": "缅甸语 Burmese", "km": "高棉语 Khmer", "lo": "老挝语 Lao",
    "ka": "格鲁吉亚语 Georgian", "hy": "亚美尼亚语 Armenian", "az": "阿塞拜疆语 Azerbaijani",
    "kk": "哈萨克语 Kazakh", "uz": "乌兹别克语 Uzbek", "mn": "蒙古语 Mongolian",
    "sw": "斯瓦希里语 Swahili", "af": "南非荷兰语 Afrikaans", "sq": "阿尔巴尼亚语 Albanian",
    "mk": "马其顿语 Macedonian", "be": "白俄罗斯语 Belarusian", "tl": "他加禄语 Tagalog",
    "la": "拉丁语 Latin", "eo": "世界语 Esperanto", "und": "未识别 Unknown",
}


def name_of(code):
    return LANG_NAMES.get(code, code)
