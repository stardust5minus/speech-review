"""Small standard-library helpers shared by the Colab launcher and tests."""
import datetime
import hashlib
import os
import shutil
import stat
import zipfile
from pathlib import Path,PurePosixPath

def extract_inputs(archive,destination):
    """Extract without path traversal, symlinks, or overwriting changed inputs.

    Restoring ZIP timestamps keeps existing alignment fingerprints stable when
    the same recording archive is uploaded to a later Colab session.
    """
    destination=Path(destination).resolve();destination.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        members=z.infolist()
        if sum(m.file_size for m in members)>8*1024**3:raise ValueError('ZIP 解压后超过 8 GB，请分受试者上传')
        planned=[]
        for m in members:
            name=m.filename.replace('\\','/')
            parts=PurePosixPath(name)
            if parts.is_absolute() or '..' in parts.parts or (parts.parts and ':' in parts.parts[0]) or stat.S_ISLNK(m.external_attr>>16):
                raise ValueError('ZIP 包含不安全路径或符号链接')
            target=(destination/Path(*parts.parts)).resolve()
            if target!=destination and destination not in target.parents:raise ValueError('ZIP 路径越界')
            if target.exists() and not m.is_dir():
                with z.open(m) as stream:incoming=hashlib.file_digest(stream,'sha256').digest()
                with target.open('rb') as stream:existing=hashlib.file_digest(stream,'sha256').digest()
                if incoming!=existing:raise ValueError(f'原始输入已改变，不能覆盖：{name}')
            planned.append((m,target))
        for m,target in planned:
            if m.is_dir():target.mkdir(parents=True,exist_ok=True);continue
            if target.exists():continue
            target.parent.mkdir(parents=True,exist_ok=True)
            with z.open(m) as src,target.open('wb') as dst:shutil.copyfileobj(src,dst)
            timestamp=datetime.datetime(*m.date_time,tzinfo=datetime.timezone.utc).timestamp()
            os.utime(target,(timestamp,timestamp))
    return sorted({p.parent for p in destination.rglob('*') if p.is_file() and p.suffix.lower()=='.wav' and '__MACOSX' not in p.parts},key=str)
