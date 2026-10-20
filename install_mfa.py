"""Prepare an isolated, project-local Windows/Linux MFA environment.

Run with Python 3.11/3.12; this does not modify shell profiles or global Conda.
"""
import io
import os
import platform
import subprocess
import tarfile
import urllib.request
from pathlib import Path

root=Path(__file__).resolve().parent
runtime=root/'runtime'
runtime.mkdir(exist_ok=True)
windows=platform.system()=='Windows'
if platform.machine().lower() not in ('amd64','x86_64') or platform.system() not in ('Windows','Linux'):
    raise RuntimeError('此安装脚本支持 Windows x64 与 Colab/Linux x64')
subdir='win-64' if windows else 'linux-64'
exe=runtime/('micromamba.exe' if windows else 'micromamba')
if not exe.exists():
    print('Downloading micromamba from the official distribution...',flush=True)
    data=urllib.request.urlopen(f'https://micro.mamba.pm/api/micromamba/{subdir}/latest',timeout=180).read()
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:bz2') as archive:
        member=next(m for m in archive.getmembers() if m.name.replace('\\','/').endswith('/micromamba.exe' if windows else '/micromamba'))
        exe.write_bytes(archive.extractfile(member).read())
if not windows:exe.chmod(exe.stat().st_mode|0o111)
if not (runtime/'mfa'/('Scripts' if windows else 'bin')/('mfa.exe' if windows else 'mfa')).exists():
    subprocess.run([str(exe),'--root-prefix',str(runtime/'mamba'),'create','-p',str(runtime/'mfa'),'-c','conda-forge','--override-channels','python=3.11','montreal-forced-aligner=3.3.10','-y'],check=True)
print('MFA environment ready. Mandarin models will be prepared at first alignment.',flush=True)
