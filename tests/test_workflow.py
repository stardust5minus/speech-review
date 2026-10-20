import io
import tempfile
import unittest
import wave
import zipfile
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend import storage, qc, transcription
from backend.main import app, run_job, jobs

class Workflow(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.patch=patch.object(storage,'DATA',self.root/'data'); self.patch.start()
        folder=self.root/'029';folder.mkdir()
        self.wav=folder/'3nonhomo_029_trial12.wav'
        with wave.open(str(self.wav),'wb') as w:
            w.setparams((1,2,16000,0,'NONE','not compressed'));w.writeframes(b'\0\0'*16000)
        self.txt=self.wav.with_suffix('.txt');self.txt.write_text('原始参考',encoding='utf-8')
        self.client=TestClient(app,base_url='http://127.0.0.1')
        r=self.client.post('/api/import',json={'folder':str(folder)})
        self.assertEqual(r.status_code,200,r.text)
        self.pid=r.json()['id']
    def tearDown(self):
        self.patch.stop();self.tmp.cleanup()
    def asr(self,text):
        jobs['test']={'errors':[],'done':0,'status':'running'}
        with patch('backend.transcription.transcribe',return_value={'raw':text,'avg_logprob':-0.5,'segments':[]}):
            run_job('test',self.pid,['1'])
        self.assertEqual(jobs['test']['errors'],[])
    def test_preservation_and_export(self):
        self.asr('指呃指')
        t=storage.read(self.pid)['trials'][0]
        self.assertEqual(t['asr']['raw'],'指呃指')
        self.assertEqual(t['corrected'],'指 呃 指')
        r=self.client.put(f'/api/projects/{self.pid}/trials/1',json={'corrected':'纸 呃 指','labels':['disfluency'],'notes':'人工决定','complete':True})
        self.assertEqual(r.status_code,200)
        self.asr('梦')
        t=storage.read(self.pid)['trials'][0]
        self.assertEqual(t['corrected'],'纸 呃 指')
        self.assertEqual(t['labels'],['disfluency'])
        self.assertEqual(t['asr_history'][0]['raw'],'指呃指')
        self.assertEqual(self.txt.read_text(encoding='utf-8'),'原始参考')
        data=self.client.get(f'/api/projects/{self.pid}/export').content
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            self.assertEqual(z.namelist(),[self.txt.name])
            self.assertEqual(z.read(self.txt.name).decode(),'纸 呃 指\n')
        reopened=self.client.post('/api/import',json={'folder':str(self.wav.parent)}).json()
        self.assertEqual(reopened['id'],self.pid)
        self.assertTrue(reopened['trials'][0]['complete'])
    def test_no_unsaved_export(self):
        self.asr('三四')
        with zipfile.ZipFile(io.BytesIO(self.client.get(f'/api/projects/{self.pid}/export').content)) as z:
            self.assertEqual(z.namelist(),[])
    def test_origin_protection(self):
        r=self.client.post('/api/import',headers={'Origin':'https://example.com'},json={'folder':str(self.wav.parent)})
        self.assertEqual(r.status_code,403)
    def test_bulk_save_payload_and_original_protection(self):
        r=self.client.post(f'/api/projects/{self.pid}/save-all',json={'trials':[{'id':'1','corrected':'三 呃 四','labels':['disfluency'],'notes':'批量修改','complete':False}]})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()['errors'],[])
        self.assertTrue(r.json()['saved'][0]['saved'])
        self.assertFalse(r.json()['saved'][0]['complete'])
        self.assertEqual(self.txt.read_text(encoding='utf-8'),'原始参考')
        self.assertEqual((storage.DATA/self.pid/'corrected'/self.txt.name).read_text(encoding='utf-8'),'三 呃 四\n')
        self.assertEqual(self.client.post(f'/api/projects/{self.pid}/save-all',json={'trials':[{'id':'999','corrected':'错'}]}).status_code,400)
    def test_aiff_named_wav_playback(self):
        import av
        import hashlib
        # Reproduce the actual recordings: AIFF payload with a .wav extension.
        with av.open(str(self.wav),'w',format='aiff') as dest:
            stream=dest.add_stream('pcm_s16be',rate=44100)
            stream.layout='mono'
            frame=av.AudioFrame(format='s16',layout='mono',samples=4410)
            frame.sample_rate=44100
            frame.planes[0].update(bytes(frame.planes[0].buffer_size))
            for packet in stream.encode(frame): dest.mux(packet)
            for packet in stream.encode(None): dest.mux(packet)
        before=hashlib.sha256(self.wav.read_bytes()).digest()
        r=self.client.get(f'/api/projects/{self.pid}/trials/1/audio')
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.content[:4],b'RIFF')
        with wave.open(io.BytesIO(r.content),'rb') as w:
            self.assertEqual(w.getframerate(),44100)
            self.assertEqual(w.getnframes(),4410)
            self.assertEqual(w.getsampwidth(),2)
        self.assertEqual(before,hashlib.sha256(self.wav.read_bytes()).digest())
        samples=transcription.decode_audio(self.wav)
        self.assertEqual(str(samples.dtype),'float32')
        self.assertEqual(samples.ndim,1)
        self.assertEqual(len(samples),1600)
        ranged=self.client.get(f'/api/projects/{self.pid}/trials/1/audio',headers={'Range':'bytes=0-43'})
        self.assertEqual(ranged.status_code,206)
        self.assertEqual(len(ranged.content),44)
    def test_one_click_and_job_recovery(self):
        import time
        result={'raw':'三 呃 四','avg_logprob':-0.4,'segments':[],'profile':'nonhomo','pipeline_version':'notebook-v1'}
        with patch('backend.transcription.transcribe',return_value=result):
            r=self.client.post(f'/api/projects/{self.pid}/transcribe')
            self.assertEqual(r.status_code,200,r.text)
            jid=r.json()['id']
            for _ in range(100):
                j=self.client.get('/api/jobs/'+jid).json()
                if j['status']=='finished': break
                time.sleep(.01)
            self.assertEqual(j['status'],'finished')
            self.assertEqual(j['done'],1)
            self.assertEqual(j['errors'],[])
            self.assertEqual(self.client.get(f'/api/projects/{self.pid}/job').json()['id'],jid)
            self.assertTrue((storage.DATA/'job_state'/(jid+'.json')).exists())
            self.assertEqual(storage.read(self.pid)['trials'][0]['corrected'],'三 呃 四')
            self.assertEqual(self.client.post(f'/api/projects/{self.pid}/transcribe').status_code,400)
    def test_qc_keeps_repetitions_and_fillers(self):
        text='梦课梦那个呃额额'
        result=qc.analyze(text,'nonhomo')
        self.assertEqual(result['spaced'],'梦 课 梦 那 个 呃 额 额')
        self.assertTrue(any(i['kind']=='self_correction' for i in result['issues']))

if __name__=='__main__':unittest.main()
