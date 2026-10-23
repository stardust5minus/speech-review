import hashlib
import json
import shutil
import threading
import time
import uuid
import wave
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from . import storage,textgrid,mfa_runtime
from .audio import playback_wav

pool=ThreadPoolExecutor(max_workers=1)
LOCK=threading.RLock()
jobs={}

def fingerprint(path):
    st=Path(path).stat()
    return {'size':st.st_size,'mtime_ns':st.st_mtime_ns}

def duration(path):
    with wave.open(str(playback_wav(path)),'rb') as wav:
        return wav.getnframes()/wav.getframerate()

def valid_for(record,trial):
    if not record or record['transcript']!=trial.get('corrected'):return False
    try:return record['audio_reference']==fingerprint(trial['audio_path'])
    except OSError:return False

def view(pid,tid):
    t=storage.trial(storage.read(pid),tid)
    result={}
    for version in ('auto','reviewed'):
        record=t.get('alignments',{}).get(version)
        result[version]={**record,'stale':not valid_for(record,t)} if record else None
    return result

def save_version(pid,tid,version,record,base_id=None,previous_transcript=None,reset_reviewed=False,expected_reviewed_id=None):
    def apply(t):
        if t.get('corrected')!=(previous_transcript if previous_transcript is not None else record['transcript']) or fingerprint(t['audio_path'])!=record['audio_reference']:
            raise ValueError('转写或音频已改变，不能保存本次边界；请重新对齐')
        current=t.setdefault('alignments',{})
        if base_id and base_id not in [r['id'] for r in current.values() if r]:
            raise ValueError('对齐版本已经更新，请重新载入后编辑')
        if reset_reviewed and (current.get('reviewed') or {}).get('id')!=expected_reviewed_id:
            raise ValueError('Manual alignment changed during MFA; reload before resetting')
        if reset_reviewed and current.get('reviewed'):
            t.setdefault('alignment_history',[]).append({'version':'reviewed',**current.pop('reviewed'),'archived_reason':'MFA reset'})
        old=current.get(version)
        if old:t.setdefault('alignment_history',[]).append({'version':version,**old})
        current[version]=record
        filename=f'{Path(t["filename"]).stem}_{version}.TextGrid'
        # Every version has an immutable artifact. Downloads use committed JSON,
        # so an interrupted write cannot replace an already reviewed download.
        storage.atomic(storage.DATA/pid/'textgrids'/'versions'/(record['id']+'.TextGrid'),textgrid.serialize(record['intervals'],record['duration']))
        if previous_transcript is not None and record['transcript']!=t['corrected']:
            from datetime import datetime,timezone
            t['history'].append({k:t[k] for k in ('corrected','labels','notes','complete')}|{'time':datetime.now(timezone.utc).isoformat(),'source':'TextGrid editor'})
            t['corrected']=record['transcript']
            storage.atomic(storage.DATA/pid/'corrected'/t['txt_name'],t['corrected']+'\n')
    storage.update(pid,tid,apply)

def make_record(t,intervals,audio_duration,engine,manual=False):
    return {'id':uuid.uuid4().hex,'transcript':t['corrected'],'transcript_sha256':hashlib.sha256(t['corrected'].encode()).hexdigest(),
        'audio_reference':fingerprint(t['audio_path']),'duration':audio_duration,'intervals':textgrid.validate(intervals,audio_duration,t['corrected'],manual=manual),
        'engine':engine,'created_at':time.time()}

def persist(jid):
    storage.atomic(storage.DATA/'alignment_jobs'/(jid+'.json'),json.dumps({'id':jid,**jobs[jid]},ensure_ascii=False))

for path in (storage.DATA/'alignment_jobs').glob('*.json'):
    try:
        j=json.loads(path.read_text(encoding='utf-8'));jid=j.pop('id')
        if j['status']=='running':j.update(status='interrupted',message='服务重启，对齐已中断，可重新运行',ended_at=time.time())
        jobs[jid]=j
    except (ValueError,KeyError):pass

def job_view(jid):
    if jid not in jobs:raise ValueError('对齐任务不存在')
    j=jobs[jid]
    return {'id':jid,**j,'elapsed_seconds':round(j.get('ended_at',time.time())-j['started_at'])}

def run_job(jid,pid,tids):
    j=jobs[jid]
    def progress(**values):j.update(values);persist(jid)
    try:
        mfa_runtime.ensure_models(progress)
        work_root=Path(os.environ['SPEECH_REVIEW_ALIGNMENT_WORK'])/pid if os.getenv('SPEECH_REVIEW_ALIGNMENT_WORK') else storage.DATA/pid/'alignment_runs'
        run_dir=work_root/uuid.uuid4().hex
        corpus=run_dir/'corpus';corpus.mkdir(parents=True)
        prepared=[]
        # One corpus invocation per request avoids recompiling the full Mandarin
        # lexicon for every trial in a participant-level batch.
        for tid in tids:
            try:
                t=storage.trial(storage.read(pid),tid)
                if not t.get('saved') or not t.get('corrected','').strip():raise ValueError('请先 Save 非空人工修订文本')
                progress(stage='preparing',message='正在准备已保存的修订文字与音频',current_trial=tid,current_filename=t['filename'])
                reference=fingerprint(t['audio_path'])
                stem='input' if len(tids)==1 else 'input_'+tid
                shutil.copyfile(playback_wav(t['audio_path']),corpus/(stem+'.wav'))
                storage.atomic(corpus/(stem+'.lab'),t['corrected']+'\n')
                if fingerprint(t['audio_path'])!=reference:raise ValueError('准备对齐时音频发生变化，请重新运行')
                prepared.append((tid,t,reference,stem))
            except Exception as exc:
                j['errors'].append({'trial':tid,'message':str(exc)})
                j['done']+=1
        if prepared:
            output_dir=run_dir/'output'
            progress(stage='aligning',message=f'MFA 正在对齐 {len(prepared)} 条已保存文本（计算声学特征和边界）')
            # The standard corpus path correctly honors --no_tokenization;
            # MFA 3.3.10 align_one has an incompatible Mandarin tokenizer branch.
            mfa_runtime.run(['align',str(corpus),'mandarin_china_mfa','mandarin_mfa',str(output_dir),
                '--no_tokenization','--output_format','long_textgrid','--clean','--single_speaker','--no_use_mp','--num_jobs','1','-t',str(run_dir/'temp')],run_dir/'mfa.log')
            for tid,t,reference,stem in prepared:
                try:
                    progress(stage='saving',message='正在校验字词顺序并保存 TextGrid',current_trial=tid,current_filename=t['filename'])
                    matches=list(output_dir.rglob(stem+'.TextGrid'))
                    if len(matches)!=1:raise ValueError('MFA 未生成此条 TextGrid，请检查运行日志中的 OOV 或音频错误')
                    audio_duration=duration(t['audio_path'])
                    intervals=textgrid.parse(matches[0],audio_duration,t['corrected'])
                    record=make_record(t,intervals,audio_duration,'MFA mandarin_mfa / mandarin_china_mfa')
                    if reference!=record['audio_reference']:raise ValueError('对齐期间音频发生变化，请重新运行')
                    record['run_id']=run_dir.name
                    save_version(pid,tid,'auto',record,reset_reviewed=j.get('reset_reviewed',False),expected_reviewed_id=j.get('expected_reviewed_id'))
                except Exception as exc:
                    j['errors'].append({'trial':tid,'message':str(exc)})
                j['done']+=1;persist(jid)
    except Exception as exc:
        j['errors'].append({'trial':'MFA 任务','message':str(exc)})
    finally:
        j.update(status='finished',stage='finished',message='MFA 对齐任务结束' if not j['errors'] else 'MFA 对齐有失败项，请查看详情',ended_at=time.time())
        persist(jid)

def start(pid,tid=None,reset_reviewed=False):
    if reset_reviewed and not tid:raise ValueError("Reset requires a single trial")
    p=storage.read(pid)
    candidates=[storage.trial(p,tid)] if tid else p['trials']
    tids=[t['id'] for t in candidates if t.get('saved') and t.get('corrected','').strip() and (tid or not any(valid_for(r,t) for r in t.get('alignments',{}).values()))]
    if not tids:raise ValueError('没有可对齐条目：请先 Save 人工修订文本；批量操作会跳过已有有效对齐的条目')
    if not mfa_runtime.available():raise ValueError('MFA 环境尚未准备好，请查看顶部环境状态和 README 安装说明')
    with LOCK:
        active=next((i for i,j in jobs.items() if j['status']=='running'),None)
        if active:
            if jobs[active]['project_id']==pid and not reset_reviewed:return job_view(active)
            raise ValueError('另一项目正在执行 MFA 对齐，请稍后再试')
        jid=uuid.uuid4().hex
        jobs[jid]={'project_id':pid,'status':'running','stage':'queued','message':'MFA 任务已提交','started_at':time.time(),'done':0,'total':len(tids),'errors':[]}
        jobs[jid].update(reset_reviewed=reset_reviewed,expected_reviewed_id=(candidates[0].get('alignments',{}).get('reviewed') or {}).get('id') if reset_reviewed else None)
        persist(jid);pool.submit(run_job,jid,pid,tids)
    return job_view(jid)

def latest_job(pid):
    found=[i for i,j in jobs.items() if j['project_id']==pid]
    return job_view(max(found,key=lambda i:jobs[i]['started_at'])) if found else None

def save_reviewed(pid,tid,intervals,transcript,base_id,update_transcript=False):
    t=storage.trial(storage.read(pid),tid)
    if not t.get('saved') or transcript!=t['corrected']:raise ValueError('文字已改变，请先保存修订文字并重新对齐')
    base=next((r for r in t.get('alignments',{}).values() if r and r['id']==base_id),None)
    if not base or not valid_for(base,t):raise ValueError('原对齐已过期，请重新载入有效对齐')
    edited=' '.join(word for i in intervals for word in i['text'].split())
    record=make_record({**t,'corrected':edited if update_transcript else transcript},intervals,base['duration'],'human reviewed',manual=update_transcript)
    record['base_id']=base_id
    save_version(pid,tid,'reviewed',record,base_id,previous_transcript=transcript if update_transcript else None)
    return view(pid,tid)

def import_reviewed(pid,tid,content):
    t=storage.trial(storage.read(pid),tid)
    if not t.get('saved') or not t.get('corrected','').strip():raise ValueError('请先 Save 人工修订文本')
    path=storage.DATA/pid/'imports'/(uuid.uuid4().hex+'.TextGrid')
    storage.atomic(path,content)
    audio_duration=duration(t['audio_path'])
    intervals=textgrid.parse(path,audio_duration,t['corrected'],manual=True)
    record=make_record(t,intervals,audio_duration,'imported human reviewed TextGrid',manual=True)
    save_version(pid,tid,'reviewed',record)
    return view(pid,tid)

def download(pid,tid,version):
    if version not in ('auto','reviewed'):raise ValueError('无效对齐版本')
    t=storage.trial(storage.read(pid),tid)
    record=t.get('alignments',{}).get(version)
    if not valid_for(record,t):raise ValueError('此版本不存在或已过期，请重新对齐')
    return textgrid.serialize(record['intervals'],record['duration'])
