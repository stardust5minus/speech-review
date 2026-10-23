"""Import existing audio/transcript/TextGrid sets into a new managed project."""
import shutil
import uuid
from pathlib import Path,PurePosixPath
from fastapi import APIRouter,Request
from starlette.datastructures import UploadFile
from . import storage,alignment,textgrid

router=APIRouter(prefix='/api')
MAX_BYTES=2*1024**3

def decode_text(raw,name):
    encodings=('utf-16',) if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else ('utf-8-sig','gb18030')
    for encoding in encodings:
        try:return raw.decode(encoding)
        except UnicodeError:pass
    raise ValueError(f'无法读取 TXT 编码：{name}')

def clean_owned(path,parent):
    path=Path(path).resolve();parent=Path(parent).resolve()
    if path!=parent and parent in path.parents and path.is_dir():shutil.rmtree(path)

def assemble(root,condition,title):
    """Validate the whole selection before creating any project or review."""
    files={p.name.casefold():p for p in root.iterdir() if p.is_file()}
    wavs=[p for p in files.values() if p.suffix.lower()=='.wav']
    if not wavs:raise ValueError('请选择 WAV、同名 TXT 和 TextGrid，或包含这些文件的文件夹。')
    prepared={};warnings=[]
    for wav in wavs:
        stem=wav.stem.casefold();txt=files.get(stem+'.txt')
        grid=next((files[name] for name in (stem+'.textgrid',stem+'_reviewed.textgrid',stem+'_auto.textgrid') if name in files),None)
        if not txt or not grid:raise ValueError(f'{wav.name} 缺少同名 '+('TXT' if not txt else 'TextGrid')+'；请同时选择三类文件。')
        original=decode_text(txt.read_bytes(),txt.name)
        try:
            audio_duration=alignment.duration(wav)
            intervals=textgrid.parse(grid,audio_duration,manual=True,flexible=True)
        except Exception as exc:raise ValueError(f'{wav.name} / {grid.name} 校验失败：{exc}') from exc
        transcript=' '.join(word for interval in intervals for word in interval['text'].split())
        if ''.join(original.split())!=''.join(transcript.split()):
            warnings.append(f'{wav.name}：TextGrid 与 TXT 文字不同；按 TextGrid 保存修订文字，原 TXT 保留在参考区。')
        prepared[wav.name]=(intervals,audio_duration,transcript,grid.name)
    project=None
    try:
        project=storage.import_folder(str(root),condition,managed=True)
        project['participant']=title or f'已有标注导入（{len(wavs)} 条）';storage.write(project)
        for trial in project['trials']:
            intervals,audio_duration,transcript,grid_name=prepared[trial['filename']]
            storage.save_review(project['id'],trial['id'],{'corrected':transcript,'labels':[],'notes':'','complete':False})
            current=storage.trial(storage.read(project['id']),trial['id'])
            record=alignment.make_record(current,intervals,audio_duration,'imported existing TextGrid',manual=True)
            record['imported_filename']=grid_name
            alignment.save_version(project['id'],trial['id'],'reviewed',record)
        return {'project':storage.read(project['id']),'warnings':warnings,'imported':len(wavs)}
    except Exception:
        if project:clean_owned(storage.DATA/project['id'],storage.DATA)
        raise

@router.post('/import-existing')
async def import_existing(request:Request):
    root=storage.DATA/'inputs'/uuid.uuid4().hex
    root.mkdir(parents=True,exist_ok=False)
    try:
        async with request.form(max_files=3000,max_fields=10) as form:
            condition=str(form.get('condition','unknown'))
            if condition not in ('unknown','number','homo','nonhomo'):raise ValueError('无效任务条件')
            title=str(form.get('title','')).strip()[:160]
            names=set();total=0;count=0
            for key,upload in form.multi_items():
                if key!='files' or not isinstance(upload,UploadFile):continue
                supplied=(upload.filename or '').replace('\\','/')
                parts=PurePosixPath(supplied)
                if parts.is_absolute() or '..' in parts.parts or ':' in supplied or '\x00' in supplied:
                    raise ValueError('文件名包含不安全路径')
                name=parts.name
                if '__MACOSX' in parts.parts or name.startswith('.'):continue
                if Path(name).suffix.lower() not in ('.wav','.txt','.textgrid'):continue
                if name.casefold() in names:raise ValueError(f'文件重名：{name}。请分批导入，避免不同文件夹的同名材料混在一起。')
                names.add(name.casefold());count+=1
                with (root/name).open('xb') as stream:
                    while chunk:=await upload.read(1024*1024):
                        total+=len(chunk)
                        if total>MAX_BYTES:raise ValueError('一次导入超过 2 GB，请分批导入。')
                        stream.write(chunk)
            if not count:raise ValueError('没有选择 WAV、TXT 或 TextGrid 文件')
        # Audio decoding / TextGrid parsing must not block other requests.
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(assemble,root,condition,title)
    except Exception:
        clean_owned(root,storage.DATA/'inputs')
        raise
