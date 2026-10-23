import io
import json
import zipfile
import csv
from pathlib import Path
from urllib.parse import quote
from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel,Field
from . import alignment,storage,mfa_runtime,exports

router=APIRouter(prefix='/api')

class Boundary(BaseModel):
    start:float
    end:float
    text:str

class Reviewed(BaseModel):
    intervals:list[Boundary]
    transcript:str
    base_id:str
    update_transcript:bool=False

class Imported(BaseModel):
    content:str=Field(max_length=5_000_000)

@router.get('/alignment/status')
def status():
    ready=mfa_runtime.available()
    return {'available':ready,'models_ready':(mfa_runtime.model_root()/'mandarin_ready.json').exists(),
        'message':'MFA 已安装；首次对齐会自动准备普通话模型' if ready else '正在准备／尚未安装 MFA 环境，请查看 README 安装说明'}

@router.post('/projects/{pid}/align')
def start(pid:str,tid:str|None=None,reset_reviewed:bool=False):return alignment.start(pid,tid,reset_reviewed)

@router.get('/projects/{pid}/alignment-job')
def latest(pid:str):return alignment.latest_job(pid)

@router.get('/alignment-jobs/{jid}')
def job(jid:str):return alignment.job_view(jid)

@router.get('/projects/{pid}/trials/{tid}/alignment')
def view(pid:str,tid:str):return alignment.view(pid,tid)

@router.put('/projects/{pid}/trials/{tid}/alignment')
def reviewed(pid:str,tid:str,body:Reviewed):
    return alignment.save_reviewed(pid,tid,[i.model_dump() for i in body.intervals],body.transcript,body.base_id,body.update_transcript)

@router.post('/projects/{pid}/trials/{tid}/alignment/import')
def imported(pid:str,tid:str,body:Imported):return alignment.import_reviewed(pid,tid,body.content)

@router.get('/projects/{pid}/trials/{tid}/textgrid')
def textgrid(pid:str,tid:str,version:str='reviewed'):
    body=alignment.download(pid,tid,version)
    t=storage.trial(storage.read(pid),tid)
    filename=Path(t['filename']).stem+'_'+version+'.TextGrid'
    return Response(body.encode('utf-8'),media_type='text/plain; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="trial{tid}_{version}.TextGrid"; filename*=UTF-8\'\'{quote(filename)}'})

def records(project):
    for t in project['trials']:
        for version,record in t.get('alignments',{}).items():
            if alignment.valid_for(record,t):
                yield t,version,record

def alignment_csv(project):
    out=io.StringIO(newline='');w=csv.writer(out)
    w.writerow(['filename','version','word','start','end'])
    for t,version,r in records(project):
        for i in r['intervals']:w.writerow([t['filename'],version,i['text'],i['start'],i['end']])
    return ('\ufeff'+out.getvalue()).encode('utf-8')

def write_grids(z,p,folder=''):
    from .textgrid import serialize
    for t,version,r in records(p):
        z.writestr(folder+Path(t['filename']).stem+'_'+version+'.TextGrid',serialize(r['intervals'],r['duration']))

@router.get('/projects/{pid}/textgrids')
def textgrids(pid:str):
    p=storage.read(pid);out=io.BytesIO()
    if not any(records(p)):
        raise ValueError('尚无有效 TextGrid：请先保存修订 TXT，再点击“一键对齐已保存条目”，等待 MFA 完成后导出。')
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:write_grids(z,p)
    return Response(out.getvalue(),media_type='application/zip',headers={'Content-Disposition':'attachment; filename="TextGrids.zip"'})

@router.get('/projects/{pid}/reviewed-textgrids')
def reviewed_textgrids(pid:str):
    from .textgrid import serialize
    p=storage.read(pid)
    selected=[(t,r) for t,version,r in records(p) if version=='reviewed']
    if not selected:raise ValueError('尚无有效人工版 TextGrid，请先保存人工边界。')
    names=[Path(t['filename']).stem+'.TextGrid' for t,r in selected]
    if len({n.casefold() for n in names})!=len(names):raise ValueError('人工版文件名重复，无法安全导出。')
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for name,(t,r) in zip(names,selected):z.writestr(name,serialize(r['intervals'],r['duration']))
    return Response(out.getvalue(),media_type='application/zip',headers={'Content-Disposition':'attachment; filename="reviewed_TextGrids.zip"'})

@router.get('/projects/{pid}/alignment.csv')
def csv_export(pid:str):
    return Response(alignment_csv(storage.read(pid)),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="alignment.csv"'})

@router.get('/projects/{pid}/export-everything')
def everything(pid:str):
    p=storage.read(pid);out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for t in p['trials']:
            if t['saved']:z.writestr('corrected_txt/'+t['txt_name'],t['corrected']+'\n')
        write_grids(z,p,'textgrids/')
        z.writestr('report.csv',exports.report(p))
        z.writestr('annotations_sheet.csv',exports.annotation_csv(p))
        z.writestr('annotations.txt',exports.annotation_text(p))
        z.writestr('alignment.csv',alignment_csv(p))
        z.writestr('export-info.json',json.dumps({'participant':p['participant'],'textgrid_note':'仅导出与当前修订文本及音频匹配的有效版本；auto 和 reviewed 分开保存'},ensure_ascii=False))
    return Response(out.getvalue(),media_type='application/zip',headers={'Content-Disposition':'attachment; filename="participant_export.zip"'})
