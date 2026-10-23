"""Windows desktop host. No research files are included in the executable."""
import argparse
import ctypes
import contextlib
import http.client
import hashlib
import json
import logging
import os
from pathlib import Path
import queue
import runpy
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from urllib.parse import urlsplit
import webbrowser

VERSION = '0.1.0'
RESOURCE_ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
if not getattr(sys, 'frozen', False):
    sys.path.insert(0,str(RESOURCE_ROOT))


def configure(home):
    home.mkdir(parents=True, exist_ok=True)
    (home/'logs').mkdir(exist_ok=True)
    os.environ.update(SPEECH_REVIEW_DATA=str(home/'data'),
                      SPEECH_REVIEW_RUNTIME=str(home/'runtime'),
                      HF_HOME=str(home/'models'/'huggingface'),
                      MFA_ROOT_DIR=str(home/'models'/'mfa'))
    # Never inherit a Colab tunnel's authentication/proxy configuration.
    for name in ('SPEECH_REVIEW_PROXY_ORIGIN','SPEECH_REVIEW_WEB_PASSWORD','SPEECH_REVIEW_WEB_USER'):
        os.environ.pop(name, None)
    for name in ('stdout','stderr'):
        if getattr(sys,name) is None:
            setattr(sys,name,(home/'logs'/'desktop.log').open('a',encoding='utf-8',buffering=1))
    logging.basicConfig(filename=home/'logs'/'desktop.log',level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')


@contextlib.contextmanager
def local_get(state,path):
    # Loopback requests must never go through a machine's HTTP proxy.
    address=urlsplit(state['url'])
    if address.hostname!='127.0.0.1':raise ValueError('Invalid local workspace address')
    connection=http.client.HTTPConnection('127.0.0.1',address.port,timeout=3)
    try:
        connection.request('GET',path)
        yield connection.getresponse()
    finally:connection.close()


def instance_alive(state):
    try:
        with local_get(state,'/api/desktop-instance') as response:
            return response.status==200 and json.load(response).get('token') == state['token']
    except (OSError,ValueError,KeyError,http.client.HTTPException) as exc:
        if not getattr(instance_alive,'logged',False):
            logging.warning('Local service probe: %r',exc);instance_alive.logged=True
        return False


def start_server(token):
    import uvicorn
    from backend.main import app
    # Insert before the static '/' mount, so the probe cannot return index.html.
    from starlette.routing import Route
    from starlette.responses import JSONResponse
    async def identity(request):
        return JSONResponse({'token':token,'version':VERSION})
    app.router.routes.insert(0,Route('/api/desktop-instance',identity))
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=0,workers=1,loop='asyncio',http='h11',log_config=None))
    worker=threading.Thread(target=server.run,daemon=True)
    worker.start()
    for _ in range(300):
        if server.started:
            port=server.servers[0].sockets[0].getsockname()[1]
            state={'url':f'http://127.0.0.1:{port}','token':token}
            if instance_alive(state):return server,worker,state
        if not worker.is_alive():raise RuntimeError('The local service stopped. See logs/desktop.log.')
        time.sleep(.1)
    server.should_exit=True
    raise RuntimeError('The local service did not start within 30 seconds. See logs/desktop.log.')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--home',type=Path)
    parser.add_argument('--install-mfa',action='store_true')
    parser.add_argument('--smoke-test',action='store_true',help='Start, probe bundled modules and UI, then stop without opening a window.')
    args=parser.parse_args()
    home=(args.home or Path(os.getenv('LOCALAPPDATA',str(Path.home())))/'SpeechReview').resolve()
    configure(home)
    import faulthandler
    trace=(home/'logs'/'startup-trace.log').open('w',encoding='utf-8')
    faulthandler.enable(trace)
    faulthandler.dump_traceback_later(20,file=trace)
    if args.install_mfa:
        with (home/'logs'/'mfa-install.log').open('w',encoding='utf-8',buffering=1) as log:
            sys.stdout=sys.stderr=log
            try:runpy.run_path(str(RESOURCE_ROOT/'install_mfa.py'),run_name='__main__')
            except Exception:
                import traceback
                traceback.print_exc()
                return 1
        return 0
    mutex=None
    if os.name=='nt':
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateMutexW.restype=ctypes.c_void_p
        key=hashlib.sha256(str(home).lower().encode()).hexdigest()[:20]
        mutex=kernel.CreateMutexW(None,False,'Local\\SpeechReview-'+key)
        if not mutex:raise ctypes.WinError(ctypes.get_last_error())
        if ctypes.get_last_error()==183:
            for _ in range(100):
                try:
                    state=json.loads((home/'desktop-session.json').read_text(encoding='utf-8'))
                    if instance_alive(state):
                        webbrowser.open(state['url']+'/?lang=en')
                        return 0
                except (OSError,ValueError):pass
                time.sleep(.1)
            raise RuntimeError('Speech Review is already starting. Please wait and try again.')
    server,worker,state=start_server(secrets.token_hex(24))
    faulthandler.cancel_dump_traceback_later()
    session=home/'desktop-session.json'
    session.write_text(json.dumps(state),encoding='utf-8')
    try:
        if args.smoke_test:
            import av,ctranslate2,faster_whisper,numpy,pypinyin,praatio,tokenizers
            import tkinter as tk
            window=tk.Tk();window.withdraw();window.update();window.destroy()
            from backend.profiles import analyze
            from backend.audio import playback_wav
            from backend.transcription import decode_audio
            from backend.textgrid import serialize,parse
            from faster_whisper.vad import get_speech_timestamps
            from faster_whisper.utils import get_assets_path
            assert (Path(get_assets_path())/'silero_vad_v6.onnx').exists() or any(Path(get_assets_path()).glob('*.onnx'))
            assert analyze('七零八一四','number')['notebook_result']
            import wave
            audio=home/'smoke.wav'
            with wave.open(str(audio),'wb') as recording:
                recording.setnchannels(1);recording.setsampwidth(2);recording.setframerate(16000)
                recording.writeframes(b'\x00\x00'*16000)
            samples=decode_audio(audio)
            assert len(samples)==16000
            assert get_speech_timestamps(samples)==[]
            grid=home/'smoke.TextGrid'
            grid.write_text(serialize([{'start':.2,'end':.8,'text':'三'}],1),encoding='utf-8')
            assert any(item['text']=='三' for item in parse(grid,1,manual=True))
            from backend import mfa_runtime
            if mfa_runtime.available():
                mfa_runtime.run(['version'],home/'logs'/'mfa-version.log',timeout=120)
            with local_get(state,'/?lang=en') as response:
                assert b'type="module"' in response.read()
            with local_get(state,'/api/projects') as response:
                assert isinstance(json.load(response),list)
            (home/'smoke-test.json').write_text(json.dumps({'passed':True,'version':VERSION,'url':state['url'],'data':os.environ['SPEECH_REVIEW_DATA']}),encoding='utf-8')
            return 0
        run_window(home,state,server)
    finally:
        server.should_exit=True
        worker.join(timeout=10)
        session.unlink(missing_ok=True)
        if mutex:
            kernel.CloseHandle.argtypes=[ctypes.c_void_p]
            kernel.CloseHandle(mutex)
    return 0


def run_window(home,state,server):
    import tkinter as tk
    from tkinter import ttk,messagebox
    root=tk.Tk()
    root.title('Speech Review '+VERSION)
    root.geometry('620x380')
    root.minsize(540,350)
    frame=ttk.Frame(root,padding=24);frame.pack(fill='both',expand=True)
    ttk.Label(frame,text='Speech Review',font=('Segoe UI',22,'bold')).pack(anchor='w')
    ttk.Label(frame,text='Whisper • Human review • MFA • TextGrid',font=('Segoe UI',11)).pack(anchor='w',pady=(4,18))
    status=tk.StringVar(value='Ready. The workspace opens in your browser. / 工作台已就绪')
    ttk.Label(frame,textvariable=status,wraplength=550).pack(anchor='w',pady=(0,12))
    def open_workspace():webbrowser.open(state['url']+'/?lang=en')
    ttk.Button(frame,text='Open workspace / 打开工作台',command=open_workspace).pack(fill='x',pady=4)
    events=queue.Queue();installing=[False];closing=[False]
    def install():
        if installing[0]:return
        installing[0]=True;install_button.config(state='disabled')
        status.set('Installing MFA. First download may take several minutes. / 正在安装 MFA…')
        def work():
            try:
                command=([sys.executable] if getattr(sys,'frozen',False) else [sys.executable,str(Path(__file__).resolve())])+['--home',str(home),'--install-mfa']
                result=subprocess.run(command,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                events.put(None if result.returncode==0 else 'MFA installation failed. Open logs/mfa-install.log, then retry.')
            except Exception as exc:events.put(str(exc))
        threading.Thread(target=work,daemon=True).start()
    install_button=ttk.Button(frame,text='Install MFA (first use) / 安装 MFA（首次使用）',command=install)
    install_button.pack(fill='x',pady=4)
    ttk.Button(frame,text='Open saved data & logs / 打开数据与日志目录',command=lambda:os.startfile(str(home))).pack(fill='x',pady=4)
    ttk.Label(frame,text='Models download on first use. Keep this window open while working.\n首次使用需联网下载模型；使用期间请保留此窗口。',wraplength=550).pack(anchor='w',pady=12)
    def close():
        if closing[0]:return
        if not messagebox.askokcancel('Stop Speech Review','Save your text and boundaries in the browser first.\nStop the workspace now?\n\n请先保存文字和边界。现在停止工作台？'):return
        if installing[0]:
            messagebox.showinfo('MFA installation','Wait for MFA installation to finish before closing. / 请等待 MFA 安装完成。')
            return
        closing[0]=True;server.should_exit=True;root.destroy()
    root.protocol('WM_DELETE_WINDOW',close)
    def poll():
        try:
            result=events.get_nowait();installing[0]=False;install_button.config(state='normal')
            status.set(result or 'MFA ready. Refresh the workspace before aligning. / MFA 已就绪，请刷新工作台。')
        except queue.Empty:pass
        root.after(250,poll)
    root.after(250,poll)
    root.after(600,open_workspace)
    root.mainloop()


if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    try:sys.exit(main())
    except Exception as exc:
        logging.exception('Desktop startup failed')
        if '--smoke-test' not in sys.argv:
            import tkinter.messagebox
            tkinter.messagebox.showerror('Speech Review',str(exc)+'\n\nSee %LOCALAPPDATA%\\SpeechReview\\logs\\desktop.log')
        sys.exit(1)
