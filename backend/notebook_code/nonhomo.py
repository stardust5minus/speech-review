"""Verbatim definitions from notebook cell 19 (zero-based)."""

import re

from pathlib import Path

from pypinyin import pinyin, Style

TARGETS = {"梦", "课", "鱼", "牙", "秋", "鼓", "妈", "街", "纸"}

FILLERS = {"嗯", "额", "呃", "啊", "哎", "不", "那个", "就是", "然后", "呐", "嘛", "诶"}

TARGET_PINYIN = {
    "梦": ("meng", 4),
    "课": ("ke",   4),
    "鱼": ("yu",   2),
    "牙": ("ya",   2),
    "秋": ("qiu",  1),
    "鼓": ("gu",   3),
    "妈": ("ma",   1),
    "街": ("jie",  1),
    "纸": ("zhi",  3),
}

PINYIN_TO_TARGET = {
    "meng": "梦",
    "ke":   "课",
    "yu":   "鱼",
    "ya":   "牙",
    "qiu":  "秋",
    "gu":   "鼓",
    "ma":   "妈",
    "jie":  "街",
    "zhi":  "纸",
}

FORCE_MAP = {
    # 纸 zhi3
    "指": "纸",
    "只": "纸",
    "止": "纸",
    "趾": "纸",

    # 课 ke4
    "刻": "课",
    "克": "课",
    "客": "课",

    # 鱼 yu2
    "渔": "鱼",
    "愉": "鱼",
    "娱": "鱼",
    "于": "鱼",

    # 牙 ya2
    "芽": "牙",
    "崖": "牙",

    # 秋 qiu1
    "丘": "秋",
    "邱": "秋",

    # 鼓 gu3
    "古": "鼓",
    "谷": "鼓",
    "股": "鼓",
    "骨": "鼓",

    # 街 jie1
    "阶": "街",
    "接": "街",   # 这个一般是 jie1，可保留

    # 梦 meng4
    "孟": "梦",
    "阶": "街",
    "接": "街",
"皆": "街",
}

PINYIN_SEQ_MAP = {
    # 梦 meng
    "meng": "梦", "méng": "梦", "měng": "梦", "mèng": "梦",
    # 课 ke
    "ke": "课", "kē": "课", "ké": "课", "kě": "课", "kè": "课",
    # 鱼 yu
    "yu": "鱼", "yū": "鱼", "yú": "鱼", "yǔ": "鱼", "yù": "鱼",
    # 牙 ya
    "ya": "牙", "yā": "牙", "yá": "牙", "yǎ": "牙", "yà": "牙",
    # 秋 qiu
    "qiu": "秋", "qiū": "秋", "qiú": "秋", "qiǔ": "秋", "qiù": "秋",
    # 鼓 gu
    "gu": "鼓", "gū": "鼓", "gú": "鼓", "gǔ": "鼓", "gù": "鼓",
    # 妈 ma
    "ma": "妈", "mā": "妈", "má": "妈", "mǎ": "妈", "mà": "妈",
    # 街 jie
    "jie": "街", "jiē": "街", "jié": "街", "jiě": "街", "jiè": "街",
    # 纸 zhi
    "zhi": "纸", "zhī": "纸", "zhí": "纸", "zhǐ": "纸", "zhì": "纸",
}

PROMPT = (
    "以下是一段中文单字朗读录音。"
    "说话人只会说这九个字之一：梦 课 鱼 牙 秋 鼓 妈 街 纸。"
    "每次只说一个字，可能重复或有口吃。"
    "【重要】输出只能包含这九个字和口吃词（嗯 额 呃 啊），不能出现其他任何字。"
    "特别注意：纸(zhi3) 不要写成 指枝只芝直知之；"
    "街(jie1) 不要写成 姐结节；"
    "鱼(yu2) 不要写成 与雨语于；"
    "鼓(gu3) 不要写成 固古谷；"
    "妈(ma1) 不要写成 马吗骂；"
    "课(ke4) 不要写成 科可刻。"
    "如果听到拼音请转成对应汉字："
    "meng→梦 ke→课 yu→鱼 ya→牙 qiu→秋 gu→鼓 ma→妈 jie→街 zhi→纸。"
    "请逐字输出，不要添加标点。"
)

def preprocess_raw(text: str) -> str:
    """
    处理 Whisper 把拼音逐字母/音节输出的情况，例如：
      y u - m e n g - j i e  →  yu meng jie
      q i ū                  →  qiū
      k è                    →  kè
    步骤：先把连字符周围的空格去掉，再把被空格隔开的单字母序列合并。
    """
    # 1. 把 "x - y" 里的连字符两侧空格去掉 → "x-y"，再把连字符换成空格
    text = re.sub(r"\s*[-–]\s*", " ", text)

    # 2. 把连续的单字符 token（含 unicode 声调字母）合并成一个词
    #    匹配：一个字母（含声调）后跟一个空格，重复多次，最后一个字母
    def merge_single_chars(m):
        return m.group(0).replace(" ", "")

    # 先处理带声调 unicode 字母序列（如 q i ū → qiū）
    text = re.sub(
        r'(?<!\w)([a-zA-Zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü]'
        r'(?:\s[a-zA-Zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü])+)(?!\w)',
        merge_single_chars,
        text
    )
    return text

def tokenize_zh(text: str) -> list[str]:
    """切分 token：中文按字，英文/拼音按词保留（转小写）"""
    t = (text or "").strip()
    # 去掉标点（注意转义正确）
    t = re.sub(r'[，。,\.!！\?？:：;；"""（）\(\)\[\]{}<>、…]', " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    if not t:
        return []
    tokens = []
    for p in t.split(" "):
        if not p:
            continue
        # 纯英文/拼音词（含 unicode 声调字母）保留为整体
        if re.fullmatch(r"[A-Za-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü0-9]+", p):
            tokens.append(p.lower())
        else:
            tokens.extend(list(p))
    return tokens

def normalize_tokens(tokens: list[str]) -> list[str]:
    """
    规范化：
    1. 拼音序列词（含声调）→ 目标汉字
    2. 去掉孤立数字/声调残留
    3. FORCE_MAP：误识别字 → 目标词
    """
    result = []
    for t in tokens:
        # 先查带声调的完整拼音映射
        if t in PINYIN_SEQ_MAP:
            result.append(PINYIN_SEQ_MAP[t])
            continue
        # 去掉末尾数字后查拼音映射
        base = re.sub(r"[0-9]+$", "", t)
        if base in PINYIN_TO_TARGET:
            result.append(PINYIN_TO_TARGET[base])
            continue
        # 跳过孤立数字/连字符
        if re.fullmatch(r"[0-9\-]+", t):
            continue
        # FORCE_MAP
        if t in FORCE_MAP:
            result.append(FORCE_MAP[t])
            continue
        result.append(t)
    return result

def deduplicate(tokens: list[str]) -> tuple[list[str], bool]:
    """
    检测并去除 Whisper 幻觉重复。
    如果后半段和前半段完全一样，只保留前半段。
    返回 (去重后的tokens, 是否发现重复)
    """
    n = len(tokens)
    for half in range(1, n // 2 + 1):
        if tokens[:half] == tokens[n - half:]:
            return tokens[:half], True
    return tokens, False

def get_pinyin_key(char: str) -> tuple:
    try:
        py = pinyin(char, style=Style.TONE3, strict=False)[0][0]
        base = re.sub(r"[0-9]", "", py)
        tone_match = re.findall(r"[0-9]", py)
        tone = int(tone_match[0]) if tone_match else 0
        return base, tone
    except Exception:
        return None, None

def classify_token(token: str) -> tuple:
    if token in TARGETS:
        return "correct", token
    if token in FILLERS:
        return "filler", None
    base, tone = get_pinyin_key(token)
    if base:
        for target, (tb, tt) in TARGET_PINYIN.items():
            if base == tb:
                if tone == tt:
                    return "correct", target
                else:
                    return "wrong_pronunciation", target
    return "wrong_word", None

def detect_silent(tokens: list[str]) -> bool:
    return len(tokens) == 0

def detect_disfluency(tokens: list[str]) -> bool:
    return any(t in FILLERS for t in tokens)

def detect_self_correction(tokens: list[str]) -> bool:
    if not tokens:
        return False
    joined = "".join(tokens)
    if re.search(r"(重来|重新|再来|从头|重头|不对|不是|说错|改口|更正)", joined):
        return True
    seq = []
    for t in tokens:
        label, target = classify_token(t)
        if target:
            seq.append(target)
    # 同一目标词出现超过一次
    if len(seq) != len(set(seq)):
        return True
    # X filler X 模式
    for i in range(len(tokens) - 2):
        _, t1 = classify_token(tokens[i])
        _, t3 = classify_token(tokens[i + 2])
        if t1 and t1 == t3 and tokens[i + 1] in FILLERS:
            return True
    return False

def detect_issues(tokens: list[str]) -> dict:
    wrong_pron = []
    wrong_word = []
    for t in tokens:
        label, _ = classify_token(t)
        if label == "wrong_pronunciation":
            wrong_pron.append(t)
        elif label == "wrong_word":
            wrong_word.append(t)
    return {"wrong_pron": wrong_pron, "wrong_word": wrong_word}

def load_gold(wav_path: Path, gold_dir: Path):
    gold_file = gold_dir / (wav_path.stem + ".txt")
    if gold_file.exists():
        return gold_file.read_text(encoding="utf-8").strip()
    return None

def compare_with_gold(whisper_out: str, gold) -> tuple:
    if gold is None:
        return "", ""
    return gold, ("✓" if whisper_out == gold else "✗")
