"""Exercise the actual notebook setup cell without downloads or apt changes."""
import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

class ColabBootstrap(unittest.TestCase):
    def run_setup(self,installed=False,ensurepip_fails=False,venv_fails=False,pip_install_fails=False):
        root=Path(__file__).resolve().parents[1]
        notebook=root/'SpeechReview_Colab_Public.ipynb'
        if not notebook.exists():notebook=root.parent/notebook.name
        data=json.loads(notebook.read_text(encoding='utf-8'))
        code=next(''.join(c['source']) for c in data['cells'] if c['cell_type']=='code' and 'VENV_ROOT=Path' in ''.join(c['source']))
        calls=[];downloaded=[];state={'pip':installed,'venv_attempts':0}
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);python=folder/'speech_review_python'/'bin'/'python'
            if installed:python.parent.mkdir(parents=True);python.touch()
            code=code.replace('/content/',folder.as_posix()+'/')
            def run(command,**kwargs):
                calls.append(command);rc=0
                if command[1:3]==['-m','venv']:
                    self.assertIn('--without-pip',command);state['venv_attempts']+=1
                    if venv_fails and state['venv_attempts']==1:rc=1
                    else:python.parent.mkdir(parents=True,exist_ok=True);python.touch()
                elif command[1:4]==['-m','pip','--version']:rc=0 if state['pip'] else 1
                elif command[1:3]==['-m','ensurepip']:
                    rc=1 if ensurepip_fails else 0
                    if not rc:state['pip']=True
                elif command[0]==str(python) and len(command)==2 and command[1].endswith('_get_pip.py'):state['pip']=True
                elif command[1:4]==['-m','pip','install'] and pip_install_fails:rc=1
                return subprocess.CompletedProcess(command,rc)
            def download(url,destination):
                downloaded.append(url);Path(destination).write_text('# mocked bootstrap',encoding='utf-8')
            with patch('subprocess.run',side_effect=run),patch('urllib.request.urlretrieve',side_effect=download),contextlib.redirect_stdout(io.StringIO()):
                if pip_install_fails:
                    with self.assertRaisesRegex(RuntimeError,'Setup failed'):exec(compile(code,'notebook_setup','exec'),{'APP_ROOT':folder})
                else:exec(compile(code,'notebook_setup','exec'),{'APP_ROOT':folder})
            self.assertFalse((folder/'speech_review_get_pip.py').exists())
        return calls,downloaded
    def test_existing_environment_keeps_pip_and_skips_apt(self):
        calls,downloads=self.run_setup(installed=True)
        self.assertFalse(downloads);self.assertFalse(any(c[0]=='apt-get' for c in calls))
        self.assertFalse(any('ensurepip' in c for c in calls))
    def test_missing_pip_uses_ensurepip(self):
        calls,downloads=self.run_setup()
        self.assertTrue(any('ensurepip' in c for c in calls));self.assertFalse(downloads)
    def test_failed_ensurepip_uses_official_bootstrap(self):
        calls,downloads=self.run_setup(ensurepip_fails=True)
        self.assertEqual(downloads,['https://bootstrap.pypa.io/get-pip.py'])
    def test_failed_venv_installs_support_and_retries(self):
        calls,downloads=self.run_setup(venv_fails=True)
        self.assertIn(['apt-get','install','-y','python3-venv'],calls)
        self.assertEqual(sum(c[1:3]==['-m','venv'] for c in calls),2)
    def test_install_failure_is_visible_and_not_ignored(self):
        self.run_setup(installed=True,pip_install_fails=True)
