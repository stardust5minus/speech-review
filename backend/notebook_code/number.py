"""Verbatim definitions from notebook cell 9 (zero-based)."""

import re

from pathlib import Path

DIGITS = {"零","一","四","五","六","七","八","九","十"}

FILLERS = {"嗯","额","呃","啊","哎","不","那个","就是","然后","呐","嘛","诶"}

PROMPT = (
    "这是中文口播数字任务。常见词：零 一 四 五 六 七 八 九 十。"
    "说话人可能会说：嗯 额 呃 啊 不 那个 就是 然后 等口吃词。"
    "请按听到的内容逐字输出，并尽量简短。"
)

def tokenize_zh(text: str):

    t = (text or "").strip()
    t = re.sub(r"[，。,\.!！\?？:：;；\"“”\(\)\[\]{}<>]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    if not t:
        return []

    parts = t.split(" ")
    tokens = []
    for p in parts:
        if not p:
            continue
        if re.fullmatch(r"[A-Za-z]+", p):
            tokens.append(p)
            continue
        tokens.extend(list(p))
    return tokens

def detect_silent(tokens):
    return len(tokens) == 0

def detect_disfluency(tokens):
    return any(t in FILLERS for t in tokens)

def detect_self_correction(tokens):
    """
    自我纠正（疑似）：
    1) 出现显式纠正词：不对/不是/更正/重来/重新/我说错了/改口/我的意思是
    2) 出现多个不同数字（比如先说“一”又改成“五”），常见于念错后纠正
    """
    joined = "".join(tokens)
    if re.search(r"(不对|不是|更正|重来|重新|我说错了|改口|我的意思是)", joined):
        return True

    digit_seq = [t for t in tokens if t in DIGITS]
    return len(digit_seq) >= 2 and len(set(digit_seq)) >= 2

def detect_wrong_word(tokens):
    """
    wrong word（疑似）：
    出现既不是数字、也不是填充词、也不是允许杂项（比如number）的 token
    """
    allowed = set(DIGITS) | set(FILLERS) | set(ALLOW_MISC)
    bad = [t for t in tokens if t not in allowed]
    return (len(bad) > 0), bad[:20]

# Notebook cell 9 references ALLOW_MISC without defining it.
# Use its definition from the Homo script (cell 18).
ALLOW_MISC = {'number', 'Number', 'NUMBER'}
