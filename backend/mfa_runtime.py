"""Local MFA process adapter; does not change global Conda or shell settings."""
import os
import shutil
import subprocess
import platform
from pathlib import Path
from . import storage

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'runtime'

def command(args):
    explicit=os.getenv('MFA_EXECUTABLE')
    if explicit:
        return [explicit,*args]
    windows=platform.system()=='Windows'
    micro=RUNTIME/('micromamba.exe' if windows else 'micromamba')
    prefix=RUNTIME/'mfa'
    executable_in_env=prefix/('Scripts' if windows else 'bin')/('mfa.exe' if windows else 'mfa')
    if micro.exists() and executable_in_env.exists():
        return [str(micro),'--root-prefix',str(RUNTIME/'mamba'),'run','-p',str(prefix),'mfa',*args]
    executable=shutil.which('mfa')
    if executable:return [executable,*args]
    raise ValueError('尚未安装 MFA。请按 README 的 MFA 安装步骤准备运行环境，或设置 MFA_EXECUTABLE 后重启服务。')

def environment():
    env=os.environ.copy()
    env.update(MFA_ROOT_DIR=str(model_root()),PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    return env

def model_root():
    return Path(os.getenv('MFA_ROOT_DIR',str(storage.DATA/'mfa_models')))

def available():
    try:
        command([])
        return True
    except ValueError:
        return False

def run(args,log_path,timeout=1800):
    log_path=Path(log_path)
    log_path.parent.mkdir(parents=True,exist_ok=True)
    with log_path.open('w',encoding='utf-8') as log:
        result=subprocess.run(command(args),stdout=log,stderr=subprocess.STDOUT,env=environment(),timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    if result.returncode:
        tail=log_path.read_text(encoding='utf-8',errors='replace')[-4000:]
        raise ValueError(f'MFA 执行失败（日志：{log_path.name}）\n{tail}')

def ensure_models(progress):
    marker=model_root()/'mandarin_ready.json'
    if marker.exists():return
    for kind,name in [('acoustic','mandarin_mfa'),('dictionary','mandarin_china_mfa')]:
        progress(stage='models',message=f'正在准备 MFA 普通话{kind}模型：{name}，首次需要下载')
        run(['model','download',kind,name],model_root()/(kind+'-download.log'))
    storage.atomic(marker,'{"acoustic":"mandarin_mfa","dictionary":"mandarin_china_mfa"}')
