from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading
import uuid
import time
import json
import os
import base64
import secrets
from urllib.parse import urlsplit
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from . import storage, qc, transcription, exports
from .audio import playback_wav
from . import profiles

app=FastAPI(title='Speech Review — Local')
pool=ThreadPoolExecutor(max_workers=1)
jobs={}
job_lock=threading.Lock()

def persist_job(jid):
    storage.atomic(storage.DATA/'job_state'/(jid+'.json'),json.dumps({'id':jid,**jobs[jid]},ensure_ascii=False))

def job_view(jid):
    j=jobs[jid]
    return {'id':jid,**j,'elapsed_seconds':round(j.get('ended_at',time.time())-j.get('started_at',time.time()))}

# Recover history after a service restart without pretending an old worker exists.
for saved_job in (storage.DATA/'job_state').glob('*.json'):
    try:
        old=json.loads(saved_job.read_text(encoding='utf-8'))
        jid=old.pop('id')
        if old['status']=='running':
            old.update(status='interrupted',stage='interrupted',message='服务重启，任务已中断；可一键继续未处理录音',ended_at=time.time())
        jobs[jid]=old
    except (ValueError,KeyError):
        continue

@app.middleware('http')
async def local_only(request:Request,call_next):
    # A cloud launcher supplies one exact proxy origin and optional HTTP auth.
    password=os.getenv('SPEECH_REVIEW_WEB_PASSWORD','')
    if password:
        expected_user=os.getenv('SPEECH_REVIEW_WEB_USER','review')
        try:
            scheme,encoded=request.headers.get('authorization','').split(' ',1)
            if scheme.lower()!='basic':raise ValueError('scheme')
            username,provided=base64.b64decode(encoded,validate=True).decode('utf-8').split(':',1)
            valid=secrets.compare_digest(username.encode(),expected_user.encode()) & secrets.compare_digest(provided.encode(),password.encode())
        except (ValueError,UnicodeError):
            valid=False
        if not valid:
            return Response('Authentication required',401,headers={'WWW-Authenticate':'Basic realm="Speech Review", charset="UTF-8"','Cache-Control':'no-store'})
    trusted_origin=os.getenv('SPEECH_REVIEW_PROXY_ORIGIN','').rstrip('/')
    proxy=urlsplit(trusted_origin)
    if trusted_origin and (proxy.scheme!='https' or not proxy.hostname or proxy.path or proxy.query or proxy.fragment or proxy.username or proxy.password):
        return Response('Invalid proxy origin configuration',500)
    hosts={'127.0.0.1','localhost'}
    if proxy.hostname:hosts.add(proxy.hostname)
    if request.url.hostname not in hosts:
        return Response('Local host only',403)
    origin=request.headers.get('origin')
    allowed_origins={'http://'+request.headers.get('host','')}
    if trusted_origin:allowed_origins.add(trusted_origin)
    if origin and origin not in allowed_origins:
        return Response('Same-origin requests only',403)
    return await call_next(request)

@app.exception_handler(ValueError)
async def value_error(request,exc):
    from fastapi.responses import JSONResponse
    return JSONResponse({'detail':str(exc)},status_code=400)

@app.exception_handler(FileNotFoundError)
async def missing(request,exc):
    from fastapi.responses import JSONResponse
    return JSONResponse({'detail':'文件不存在，原文件可能已移动'},status_code=404)

class Import(BaseModel):
    folder:str
    condition:str='unknown'

class Review(BaseModel):
    corrected:str
    labels:list[str]=[]
    notes:str=''
    complete:bool=False

class BulkReview(Review):
    id:str

class BulkSave(BaseModel):
    trials:list[BulkReview]

@app.post('/api/projects/{pid}/save-all')
def save_all(pid:str,body:BulkSave):
    project=storage.read(pid)
    ids=[r.id for r in body.trials]
    if len(ids)!=len(set(ids)):raise ValueError('批量保存中有重复录音 ID')
    for tid in ids:storage.trial(project,tid)
    saved=[];errors=[]
    for row in body.trials:
        try:saved.append(storage.save_review(pid,row.id,row.model_dump(exclude={'id'})))
        except Exception as exc:errors.append({'trial':row.id,'message':str(exc)})
    return {'saved':saved,'errors':errors}

@app.get('/api/projects')
def projects():
    return [ {'id':p.parent.name,'participant':storage.read(p.parent.name)['participant']} for p in storage.DATA.glob('*/project.json')]

@app.post('/api/import')
def import_project(body:Import):
    if body.condition not in ('unknown','number','homo','nonhomo'):
        raise ValueError('无效条件')
    return storage.import_folder(body.folder,body.condition)

@app.get('/api/projects/{pid}')
def project(pid:str):
    return storage.read(pid)

@app.get('/api/projects/{pid}/trials/{tid}/audio')
def audio(pid:str,tid:str):
    source = storage.trial(storage.read(pid),tid)['audio_path']
    return FileResponse(playback_wav(source),media_type='audio/wav',headers={'Cache-Control':'no-cache'})

@app.put('/api/projects/{pid}/trials/{tid}')
def save(pid:str,tid:str,body:Review):
    return storage.save_review(pid,tid,body.model_dump())

def run_job(jid,pid,tids):
    job=jobs[jid]
    def progress(**values):
        job.update(values)
        persist_job(jid)
    for tid in tids:
        try:
            t=storage.trial(storage.read(pid),tid)
            progress(current_trial=tid,current_filename=t['filename'],stage='preparing',message='正在准备录音',audio_seconds=0,audio_duration=0)
            with transcription.LOCK:
                result=transcription.transcribe(t['audio_path'],progress=progress,condition=t['condition'])
            def apply(row):
                if row['asr'] is not None:
                    row['asr_history'].append(row['asr'])
                row['asr']=result
                row['qc']=qc.analyze(result['raw'],row['condition'],result['avg_logprob'])
                if not row['saved']:
                    row['corrected']=row['qc']['spaced']
            storage.update(pid,tid,apply)
        except Exception as e:
            job['errors'].append({'trial':tid,'message':str(e)})
        job['done']+=1
        persist_job(jid)
    job['status']='finished'
    job['ended_at']=time.time()
    job['stage']='finished'
    job['message']='转写结束' if not job['errors'] else '转写结束，部分录音失败；请查看错误详情并重试'
    persist_job(jid)

@app.post('/api/projects/{pid}/transcribe')
def transcribe(pid:str,tid:str|None=None):
    p=storage.read(pid)
    tids=[storage.trial(p,tid)['id']] if tid else [t['id'] for t in p['trials'] if profiles.needs_transcription(t)]
    with job_lock:
        active=next((jid for jid,j in jobs.items() if j['status']=='running'),None)
        if active:
            if jobs[active].get('project_id')==pid:
                return job_view(active)
            raise HTTPException(409,'另一项目已有转写任务进行中')
        if not tids:
            raise ValueError('全部录音已转写，无需重复运行；如需重新识别，请使用单条的重新转写按钮')
        jid=uuid.uuid4().hex
        jobs[jid]={'project_id':pid,'status':'running','stage':'queued','message':'任务已提交，准备开始','done':0,'total':len(tids),'errors':[],'started_at':time.time(),'model':transcription.os.getenv('WHISPER_MODEL','medium'),'device':transcription.os.getenv('WHISPER_DEVICE','cpu')}
        persist_job(jid)
    pool.submit(run_job,jid,pid,tids)
    return job_view(jid)

@app.get('/api/projects/{pid}/job')
def project_job(pid:str):
    storage.read(pid)
    matching=[jid for jid,j in jobs.items() if j.get('project_id')==pid]
    return job_view(max(matching,key=lambda jid:jobs[jid].get('started_at',0))) if matching else None

@app.get('/api/jobs/{jid}')
def job(jid:str):
    if jid not in jobs:
        raise HTTPException(404,'任务不存在')
    return job_view(jid)

@app.get('/api/projects/{pid}/export')
def export(pid:str):
    return Response(exports.export_zip(storage.read(pid)),media_type='application/zip',headers={'Content-Disposition':'attachment; filename="corrected_txt.zip"'})

@app.get('/api/projects/{pid}/report')
def report(pid:str):
    return Response(exports.report(storage.read(pid)),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="report.csv"'})

from .alignment_routes import router as alignment_router
app.include_router(alignment_router)
from .existing_import import router as existing_import_router
app.include_router(existing_import_router)

dist=Path(__file__).resolve().parents[1]/'frontend'/'dist'
if dist.exists():
    app.mount('/',StaticFiles(directory=dist,html=True),name='ui')
