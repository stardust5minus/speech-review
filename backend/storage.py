import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from .profiles import infer_condition

DATA = Path(os.getenv('SPEECH_REVIEW_DATA', str(Path(__file__).resolve().parents[1]/'data')))
LOCK = RLock()

def atomic(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temp.write_text(text, encoding='utf-8')
    os.replace(temp,path)

def read(pid):
    if not re.fullmatch('[a-f0-9]{32}',pid):
        raise ValueError('无效项目 ID')
    project=json.loads((DATA/pid/'project.json').read_text(encoding='utf-8'))
    for t in project['trials']:
        if t['condition']=='unknown':
            t['condition']=infer_condition(t['filename'])
    return project

def write(project):
    atomic(DATA/project['id']/'project.json',json.dumps(project,ensure_ascii=False,indent=2))

def trial(project, tid):
    for t in project['trials']:
        if t['id']==tid:
            return t
    raise ValueError('找不到此录音条目')

def update(pid,tid,fn):
    with LOCK:
        project=read(pid)
        t=trial(project,tid)
        fn(t)
        write(project)
        return t

def import_folder(folder,condition,managed=False):
    root=Path(folder).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError('请选择文件夹')
    owned_input=managed and (DATA/'inputs').resolve() in root.parents
    if (DATA.resolve()==root or DATA.resolve() in root.parents) and not owned_input:
        raise ValueError('不能导入应用的数据输出目录')
    with LOCK:
        DATA.mkdir(parents=True,exist_ok=True)
        for meta in DATA.glob('*/project.json'):
            p=read(meta.parent.name)
            if p['source']==str(root):
                if condition!='unknown':
                    for t in p['trials']:
                        if t['condition']=='unknown':t['condition']=condition
                    write(p)
                return p
        project={'id':uuid.uuid4().hex,'participant':root.name,'source':str(root),'trials':[]}
        wavs=sorted((f for f in root.iterdir() if f.is_file() and f.suffix.lower()=='.wav'),key=lambda p:[int(x) if x.isdigit() else x.lower() for x in re.split(r'(\d+)',p.name)])
        files={f.name.casefold():f for f in root.iterdir() if f.is_file()}
        for i,wav in enumerate(wavs):
            txt=files.get((wav.stem+'.txt').casefold())
            original=None
            if txt:
                raw=txt.read_bytes()
                encodings = ('utf-16',) if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else ('utf-8-sig','gb18030')
                for encoding in encodings:
                    try:
                        original=raw.decode(encoding); break
                    except UnicodeError:
                        pass
                if original is None:
                    raise ValueError(f'无法读取文本编码：{txt.name}')
            name=wav.name.lower()
            parsed=infer_condition(name,condition)
            project['trials'].append({'id':str(i+1),'filename':wav.name,'txt_name':txt.name if txt else wav.stem+'.txt','audio_path':str(wav), 'condition':parsed,'original':original,'asr':None,'asr_history':[], 'qc':None,'corrected':None,'saved':False,'complete':False,'labels':[],'notes':'','history':[]})
        if not wavs:
            raise ValueError('文件夹中没有 WAV 文件；请选择直接包含 WAV/TXT 的目录')
        write(project)
        return project

def save_review(pid,tid,payload):
    def apply(t):
        t['history'].append({k:t[k] for k in ('corrected','labels','notes','complete') } | {'time':datetime.now(timezone.utc).isoformat()})
        t.update(payload)
        t['saved']=True
        atomic(DATA/pid/'corrected'/t['txt_name'],t['corrected']+'\n')
    return update(pid,tid,apply)

def save_annotations(pid,tid,payload):
    """Save label-only work without accepting an untouched blank transcript."""
    def apply(t):
        t['history'].append({k:t[k] for k in ('corrected','labels','notes','complete')}|{'time':datetime.now(timezone.utc).isoformat(),'source':'manual annotation'})
        t.update({k:payload[k] for k in ('labels','notes','complete')})
        t['annotations_saved']=True
    return update(pid,tid,apply)
