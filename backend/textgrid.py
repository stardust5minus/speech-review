"""Praat IntervalTier serialization and strict boundary validation."""
import math
from pathlib import Path

def validate(intervals,duration,transcript=None):
    if not math.isfinite(duration) or duration<=0:
        raise ValueError('无效音频时长')
    result=[]
    previous=0.0
    for item in intervals:
        start,end=float(item['start']),float(item['end'])
        text=str(item['text'])
        if not math.isfinite(start) or not math.isfinite(end) or start<0 or end>duration+1e-7 or end<=start or start<previous-1e-7:
            raise ValueError('边界必须在音频范围内，开始小于结束，且按顺序排列、不重叠')
        if text.strip():
            if text!=text.strip() or any(c.isspace() for c in text):
                raise ValueError('一个区间应对应一个非空 token，不能包含空格')
            result.append({'start':start,'end':min(end,duration),'text':text})
        previous=end
    if transcript is not None and [i['text'] for i in result]!=transcript.split():
        raise ValueError('对齐字词与已保存修订文本不一致（可能存在缺词、合词或 OOV）；请先核查文字／词典后重新对齐，不能把不匹配结果用于分析')
    return result

def serialize(intervals,duration):
    words=validate(intervals,duration)
    parts=[]
    cursor=0.0
    for word in words:
        if word['start']>cursor:
            parts.append({'start':cursor,'end':word['start'],'text':''})
        parts.append(word)
        cursor=word['end']
    if cursor<duration:
        parts.append({'start':cursor,'end':duration,'text':''})
    def quote(text):return '"'+text.replace('"','""')+'"'
    lines=['File type = "ooTextFile"','Object class = "TextGrid"','','xmin = 0',f'xmax = {duration:.9f}','tiers? <exists>','size = 1','item []:','    item [1]:','        class = "IntervalTier"','        name = "words"','        xmin = 0',f'        xmax = {duration:.9f}',f'        intervals: size = {len(parts)}']
    for idx,part in enumerate(parts,1):
        lines.extend([f'        intervals [{idx}]:',f'            xmin = {part["start"]:.9f}',f'            xmax = {part["end"]:.9f}',f'            text = {quote(part["text"])}'])
    return '\n'.join(lines)+'\n'

def parse(path,duration=None,transcript=None):
    from praatio import textgrid as praat
    grid=praat.openTextgrid(str(path),includeEmptyIntervals=True)
    tiers=[grid.getTier(name) for name in grid.tierNames if name.lower().endswith('words')]
    if len(tiers)!=1:
        raise ValueError('TextGrid 必须有一个可明确识别的 words 区间层')
    tier=tiers[0]
    if not hasattr(tier,'entries'):
        raise ValueError('words 层必须是 IntervalTier')
    if duration is not None and (abs(grid.minTimestamp)>1e-6 or abs(grid.maxTimestamp-duration)>0.02):
        raise ValueError('TextGrid 的起止时间与完整音频不一致')
    intervals=[{'start':e.start,'end':min(e.end,duration) if duration is not None and e.end-duration<0.02 else e.end,'text':e.label} for e in tier.entries]
    return validate(intervals,duration or grid.maxTimestamp,transcript)
