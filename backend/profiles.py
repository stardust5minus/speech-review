"""Application adapter for the user's three notebook pipelines."""
import re
from .notebook_code import number, homo, nonhomo

PIPELINE_VERSION = 'notebook-v1'
MODULES = {'number':number,'homo':homo,'nonhomo':nonhomo}
HOMO_DIGITS = dict(zip('01456789', '零一四五六七八九'))
FULLWIDTH_DIGITS = str.maketrans('０１２３４５６７８９', '0123456789')
STANDALONE_TEN = re.compile(r'(?<![0-9])10(?![0-9])')

def infer_condition(filename, fallback='unknown'):
    name=filename.lower()
    for condition in ('nonhomo','homo','number'):
        if condition in name:
            return condition
    return fallback

def module(condition):
    if condition not in MODULES:
        raise ValueError('无法选择 notebook 流程：请在导入时指定 Number、Homo 或 Non-homo 条件')
    return MODULES[condition]

def parameters(condition):
    script=module(condition)
    options={'language':'zh','vad_filter':True,'initial_prompt':script.PROMPT}
    # Cell 9 deliberately leaves decoding parameters at faster-whisper defaults.
    if condition=='homo':
        options.update(temperature=0.0,beam_size=5,best_of=5,condition_on_previous_text=False)
    elif condition=='nonhomo':
        options.update(beam_size=5,temperature=0.0,condition_on_previous_text=False)
    return options

def analyze(raw,condition,confidence=None):
    script=module(condition)
    raw_tokens=script.tokenize_zh(raw)
    duplicate=False
    if condition=='nonhomo':
        prepared=script.preprocess_raw(raw)
        tokens=script.normalize_tokens(script.tokenize_zh(prepared))
        tokens,duplicate=script.deduplicate(tokens)
    elif condition=='homo':
        # Whisper sometimes formats a digit sequence like a phone number.
        grouped = re.sub(r'(?<=[0-9０-９])[-‐‑–—]+(?=[0-9０-９])', ' ', raw or '')
        grouped = STANDALONE_TEN.sub('十', grouped.translate(FULLWIDTH_DIGITS))
        tokens=script.map_numbers_to_targets([
            HOMO_DIGITS.get(t, t) for t in script.tokenize_zh(grouped)
        ])
    else:
        tokens=raw_tokens
    notebook_text=' '.join(tokens).strip()
    flags={'silent':script.detect_silent(tokens),'disfluency':script.detect_disfluency(tokens),'self_correction':script.detect_self_correction(tokens)}
    details={}
    if condition=='nonhomo':
        details=script.detect_issues(tokens)
        flags['wrong_word']=bool(details['wrong_word'])
        flags['wrong_pronunciation']=bool(details['wrong_pron'])
    else:
        wrong,bad=script.detect_wrong_word(tokens)
        flags['wrong_word']=wrong
        details['bad_words']=bad
        if condition=='homo':
            confusable,truly_wrong=script.classify_bad_words(bad)
            details.update(confusable=confusable,truly_wrong=truly_wrong,number_word_count=script.count_number_words(raw_tokens))
    messages={'silent':'原脚本判为疑似静音，需复听确认','disfluency':'原脚本检测到填充词／不流畅','self_correction':'原脚本检测到疑似自我纠正，需复听确认','wrong_word':'原脚本检测到词表外文字，需复听确认','wrong_pronunciation':'原脚本拼音规则标记疑似发音问题，需复听确认'}
    issues=[{'kind':key,'text':messages[key]} for key,value in flags.items() if value]
    if condition=='homo':
        digits=(raw or '').translate(FULLWIDTH_DIGITS)
        if STANDALONE_TEN.search(digits):
            issues.append({'kind':'ambiguous_digits','text':'单独出现的 10 暂转为「石」；如果听到的是两个字，请改为「衣 铃」。'})
        if '10' in STANDALONE_TEN.sub(' ', digits):
            issues.append({'kind':'ambiguous_digits','text':'连在数字串中的 10 暂按「衣 铃」转换；如果听到的是一个字，请改为「石」。'})
    if condition=='number' and flags['self_correction']:
        issues.append({'kind':'notebook_rule','text':'注意：Number 原脚本将两个及以上不同数字标为疑似自我纠正；正常数字序列也可能命中'})
    spaced=' '.join(raw_tokens).strip()
    if notebook_text!=spaced:
        issues.append({'kind':'possible_asr_confusion','text':'脚本处理结果与原始转写不同，尚未采用；请核对后决定'})
    if duplicate:
        issues.append({'kind':'repetition','text':'原脚本去重会删减内容；该结果仅在脚本结果栏显示，原始文字全部保留'})
    if confidence is not None and confidence < -1:
        issues.append({'kind':'low_confidence','text':f'平均 log probability 较低：{confidence:.2f}，需复听'})
    return {'spaced':spaced,'issues':issues,'suggestions':[],
        'notebook_result':notebook_text,'notebook_flags':flags,'notebook_details':details,'notebook_duplicate':duplicate,'profile':condition}

def review_prefill(result):
    return result['notebook_result'] if result['profile']=='homo' else result['spaced']

def refresh_homo_result(trial):
    asr = trial.get('asr') or {}
    if trial['condition']!='homo' or asr.get('profile')!='homo' or not isinstance(asr.get('raw'),str):
        return
    result=analyze(asr['raw'],'homo',asr.get('avg_logprob'))
    trial['qc']={**(trial.get('qc') or {}), **result}
    if not trial.get('saved') and trial.get('corrected') in (None,result['spaced']):
        trial['corrected']=review_prefill(result)

def needs_transcription(trial):
    result=trial.get('asr') or {}
    return result.get('pipeline_version')!=PIPELINE_VERSION or result.get('profile')!=trial['condition']
