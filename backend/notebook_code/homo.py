"""Verbatim definitions from notebook cell 18 (zero-based)."""

import re

from pathlib import Path

TARGETS = {"铃", "衣", "寺", "舞", "遛", "妻", "疤", "酒", "石"}

FILLERS = {"嗯", "额", "呃", "啊", "哎", "不", "那个", "就是", "然后", "呐", "嘛", "诶"}

ALLOW_MISC = {"number", "Number", "NUMBER"}

NUM_WORDS = {"零", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"}

NUM_TO_TARGET = {
    "零": "铃",
    "一": "衣",
    "四": "寺",
    "五": "舞",
    "六": "遛",
    "七": "妻",
    "八": "疤",
    "九": "酒",
    "十": "石",
}

HOMO_CONFUSABLES = {
    "铃": {"零", "聆", "令", "凌", "领"},
    "衣": {"一", "依", "医", "宜", "姨"},
    "寺": {"四", "似", "斯", "丝", "死"},
    "舞": {"五", "无", "吾", "误", "悟"},
    "遛": {"六", "留", "流", "刘", "柳"},
    "妻": {"七", "期", "凄", "棋", "奇"},
    "疤": {"八", "吧", "巴", "把", "爸"},
    "酒": {"九", "久", "旧", "就", "究"},
    "石": {"十", "时", "是", "事", "实"},
}

ALL_CONFUSABLES = {w for s in HOMO_CONFUSABLES.values() for w in s}

PROMPT = (
    "这是中文单字口播任务。常见词：铃 衣 寺 舞 遛 妻 疤 酒 石。"
    "说话人可能会说：嗯 额 呃 啊 不 那个 就是 然后 等口吃词。"
    "请按听到的内容逐字输出，并尽量简短，保留重复和口吃词。"
)

def tokenize_zh(text: str) -> list[str]:
    """把转写文本切分成字/词 token 列表（中文按字切，英文按词保留）"""
    t = (text or "").strip()
    t = re.sub(r"[，。,\.!！\?？:：;；\"""\(\)\[\]{}<>]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    if not t:
        return []
    tokens = []
    for p in t.split(" "):
        if not p:
            continue
        if re.fullmatch(r"[A-Za-z]+", p):
            tokens.append(p)
        else:
            tokens.extend(list(p))
    return tokens

def map_numbers_to_targets(tokens: list[str]) -> list[str]:
    """把数字词映射成对应的 homo 目标词（零→铃，一→衣，etc.）"""
    return [NUM_TO_TARGET.get(t, t) for t in tokens]

def detect_silent(tokens: list[str]) -> bool:
    return len(tokens) == 0

def detect_disfluency(tokens: list[str]) -> bool:
    return any(t in FILLERS for t in tokens)

def detect_self_correction(tokens: list[str]) -> bool:
    """
    判断是否存在自我纠正，三种情形：
    1. 显式纠正词（重来/不对/说错/etc.）
    2. 同一目标词连续出现（X X 或 X [填充词] X）
    3. 目标词序列出现前缀重复片段（如 酒 石 酒 石）
    """
    if not tokens:
        return False

    # 情形 1：显式纠正词
    joined = "".join(tokens)
    if re.search(r"(重来|重新|再来|从头|重头|我重说|我再说|不对|不是|说错|改口|更正)", joined):
        return True

    # 情形 2：连续重复（X X 或 X filler X）
    for i in range(len(tokens) - 1):
        if tokens[i] in TARGETS and tokens[i] == tokens[i + 1]:
            return True
    for i in range(len(tokens) - 2):
        if (tokens[i] in TARGETS
                and tokens[i + 1] in FILLERS
                and tokens[i] == tokens[i + 2]):
            return True

    # 情形 3：目标词序列中出现重复片段（长度 2 或 3）
    seq = [t for t in tokens if t in TARGETS]
    if len(seq) >= 4:
        for k in (2, 3):
            if len(seq) >= 2 * k:
                head = seq[:k]
                for j in range(1, len(seq) - k + 1):
                    if seq[j: j + k] == head:
                        return True

    return False

def detect_wrong_word(tokens: list[str]) -> tuple[bool, list[str]]:
    """
    判断是否出现"不属于目标词/填充词/允许杂项"的可疑词。
    用映射后的 tokens，所以数字词映射成目标词之后就不算异常了。
    """
    allowed = set(TARGETS) | set(FILLERS) | set(ALLOW_MISC)
    bad = [t for t in tokens if t not in allowed]
    return (len(bad) > 0), bad[:20]

def count_number_words(tokens_raw: list[str]) -> int:
    """统计原始转写里出现了几个数字词（越多说明模型越容易被同音数字吸走）"""
    return sum(1 for t in tokens_raw if t in NUM_WORDS)

def classify_bad_words(bad_words: list[str]) -> tuple[list[str], list[str]]:
    """
    把 wrong word 里的词分成两类：
    - confusable：目标词的常见误识别（可能是模型识别错，不一定是受试者说错）
    - truly_wrong：既不是目标词也不是常见误识别（更可能是受试者说了别的词）
    """
    confusable = [w for w in bad_words if w in ALL_CONFUSABLES]
    truly_wrong = [w for w in bad_words if w not in ALL_CONFUSABLES]
    return confusable, truly_wrong

def load_gold(wav_path: Path, gold_dir: Path) -> str | None:
    """读入与 wav 同名的人工校对 txt，不存在则返回 None"""
    gold_file = gold_dir / (wav_path.stem + ".txt")
    if gold_file.exists():
        return gold_file.read_text(encoding="utf-8").strip()
    return None

def compare_with_gold(whisper_out: str, gold: str | None) -> tuple[str, str]:
    """
    返回 (gold文本, 是否一致)
    一致 = "✓"，不一致 = "✗"，无参考 = ""
    """
    if gold is None:
        return "", ""
    match = "✓" if whisper_out == gold else "✗"
    return gold, match
