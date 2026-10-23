"""Launch separately installed tools without inheriting frozen-app DLL paths."""
import os
import subprocess
import sys
import threading

_launch_lock=threading.Lock()


def run(command,*,timeout=None,check=False,**kwargs):
    with _launch_lock:
        frozen=os.name=='nt' and bool(getattr(sys,'frozen',False))
        if frozen:
            import ctypes
            kernel=ctypes.windll.kernel32
            previous=ctypes.create_unicode_buffer(32768)
            kernel.GetDllDirectoryW(len(previous),previous)
            env=dict(kwargs.get('env') or os.environ)
            bundle=os.path.normcase(os.path.abspath(sys._MEIPASS))
            env['PATH']=os.pathsep.join(part for part in env.get('PATH','').split(os.pathsep)
                if part and not os.path.normcase(os.path.abspath(part)).startswith(bundle+os.sep)
                and os.path.normcase(os.path.abspath(part))!=bundle)
            kwargs['env']=env
            kernel.SetDllDirectoryW(None)
        try:
            process=subprocess.Popen(command,**kwargs)
        finally:
            if frozen:kernel.SetDllDirectoryW(previous.value or None)
    with process:
        try:stdout,stderr=process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill();process.communicate()
            raise
        result=subprocess.CompletedProcess(command,process.returncode,stdout,stderr)
        if check:result.check_returncode()
        return result
