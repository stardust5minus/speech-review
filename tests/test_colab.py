import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend import storage,mfa_runtime
from backend.main import app
from colab_support import extract_inputs

class ColabSupport(unittest.TestCase):
    def test_public_auth_covers_ui_audio_and_api(self):
        with tempfile.TemporaryDirectory() as root,patch.object(storage,'DATA',Path(root)),patch.dict('os.environ',{'SPEECH_REVIEW_WEB_PASSWORD':'test-secret','SPEECH_REVIEW_WEB_USER':'review','SPEECH_REVIEW_PROXY_ORIGIN':'https://demo.trycloudflare.com'}):
            client=TestClient(app,base_url='https://demo.trycloudflare.com')
            for path in ('/','/assets/example.js','/api/projects','/api/audio/example'):
                self.assertEqual(client.get(path).status_code,401)
                self.assertEqual(client.get(path,auth=('review','wrong')).status_code,401)
            self.assertEqual(client.get('/api/projects',auth=('review','test-secret')).status_code,200)
            self.assertEqual(client.get('/api/projects',auth=('review','test-secret'),headers={'Origin':'https://evil.example'}).status_code,403)
            self.assertEqual(client.get('/api/projects',headers={'Authorization':'Basic %%%'}).status_code,401)
    def test_linux_mfa_command(self):
        with tempfile.TemporaryDirectory() as root:
            runtime=Path(root);(runtime/'micromamba').touch();(runtime/'mfa'/'bin').mkdir(parents=True);(runtime/'mfa'/'bin'/'mfa').touch()
            with patch.object(mfa_runtime,'RUNTIME',runtime),patch.object(mfa_runtime.platform,'system',return_value='Linux'),patch.dict('os.environ',{'MFA_EXECUTABLE':''}):
                command=mfa_runtime.command(['version'])
            self.assertEqual(command[0],str(runtime/'micromamba'))
            self.assertEqual(command[-2:],['mfa','version'])
    def test_exact_proxy_origin_only(self):
        with tempfile.TemporaryDirectory() as root,patch.object(storage,'DATA',Path(root)),patch.dict('os.environ',{'SPEECH_REVIEW_PROXY_ORIGIN':'https://demo.colab.googleusercontent.com'}):
            client=TestClient(app,base_url='https://demo.colab.googleusercontent.com')
            self.assertEqual(client.get('/api/projects',headers={'Origin':'https://demo.colab.googleusercontent.com'}).status_code,200)
            self.assertEqual(client.get('/api/projects',headers={'Origin':'https://evil.example'}).status_code,403)
            self.assertEqual(client.get('/api/projects',headers={'Host':'different.colab.googleusercontent.com'}).status_code,403)
        with patch.dict('os.environ',{'SPEECH_REVIEW_PROXY_ORIGIN':'https://demo.example/unsafe'}):
            self.assertEqual(TestClient(app,base_url='http://127.0.0.1').get('/api/projects').status_code,500)
    def test_zip_preserves_inputs_and_blocks_traversal(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);archive=root/'input.zip'
            with zipfile.ZipFile(archive,'w') as z:z.writestr('029/Trial.WAV',b'original');z.writestr('029/Trial.txt','三 四')
            folders=extract_inputs(archive,root/'inputs');wav=folders[0]/'Trial.WAV';mtime=wav.stat().st_mtime_ns
            self.assertEqual(extract_inputs(archive,root/'inputs'),folders);self.assertEqual(wav.stat().st_mtime_ns,mtime)
            wav.write_bytes(b'changed')
            with self.assertRaises(ValueError):extract_inputs(archive,root/'inputs')
            with zipfile.ZipFile(archive,'w') as z:z.writestr('../escape.wav',b'bad')
            with self.assertRaises(ValueError):extract_inputs(archive,root/'inputs')

if __name__=='__main__':unittest.main()
