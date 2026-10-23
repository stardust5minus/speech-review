import io
import tempfile
import unittest
import wave
import zipfile
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend import storage,textgrid,alignment
from backend.main import app

class ExistingImport(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.patch=patch.object(storage,'DATA',self.root/'data');self.patch.start()
        self.client=TestClient(app,base_url='http://127.0.0.1')
        stream=io.BytesIO()
        with wave.open(stream,'wb') as w:w.setparams((1,2,16000,0,'NONE',''));w.writeframes(bytes(32000))
        self.wav=stream.getvalue()
        self.intervals=[{'start':0,'end':.3,'text':''},{'start':.3,'end':.6,'text':'三'},{'start':.6,'end':1,'text':'四'}]
        self.grid=textgrid.serialize(self.intervals,1).encode()
    def tearDown(self):self.patch.stop();self.tmp.cleanup()
    def files(self,stem='3nonhomo_069_trial9',grid_suffix='',txt='三 四'):
        return [('files',(stem+'.wav',self.wav,'audio/wav')),('files',(stem+'.txt',txt.encode(),'text/plain')),('files',(stem+grid_suffix+'.TextGrid',self.grid,'text/plain'))]
    def post(self,files,**data):return self.client.post('/api/import-existing',files=files,data=data)
    def test_ready_to_edit_original_preserved_and_export_named(self):
        with patch('backend.mfa_runtime.run') as mfa:
            r=self.post(self.files(),title='Existing annotation');self.assertEqual(r.status_code,200,r.text);mfa.assert_not_called()
        p=r.json()['project'];t=p['trials'][0]
        self.assertEqual(p['participant'],'Existing annotation')
        self.assertEqual(t['original'],'三 四');self.assertEqual(t['corrected'],'三 四');self.assertTrue(t['saved']);self.assertIsNone(t['asr'])
        self.assertEqual(t['condition'],'nonhomo')
        record=alignment.view(p['id'],t['id'])['reviewed'];self.assertFalse(record['stale']);self.assertEqual(record['intervals'],self.intervals)
        self.assertEqual(Path(t['audio_path']).read_bytes(),self.wav)
        self.assertEqual((Path(p['source'])/'3nonhomo_069_trial9.txt').read_text(encoding='utf-8'),'三 四')
        self.assertEqual((Path(p['source'])/'3nonhomo_069_trial9.TextGrid').read_bytes(),self.grid)
        z=self.client.get(f'/api/projects/{p["id"]}/reviewed-textgrids')
        with zipfile.ZipFile(io.BytesIO(z.content)) as archive:self.assertEqual(archive.namelist(),['3nonhomo_069_trial9.TextGrid'])
        # Re-upload creates an independent project and leaves the first intact.
        again=self.post(self.files()).json()['project'];self.assertNotEqual(p['id'],again['id'])
        self.assertEqual(storage.read(p['id'])['trials'][0]['corrected'],'三 四')
    def test_folder_upload_utf16_reviewed_suffix_and_txt_mismatch(self):
        files=self.files(grid_suffix='_reviewed',txt='旧 文本')
        files=[(key,('subject/'+name,body,typ)) for key,(name,body,typ) in files]
        key,(name,_,typ)=files[-1];files[-1]=(key,(name,self.grid.decode().encode('utf-16'),typ))
        r=self.post(files);self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(len(r.json()['warnings']),1)
        row=r.json()['project']['trials'][0];self.assertEqual(row['original'],'旧 文本');self.assertEqual(row['corrected'],'三 四')
    def test_batch_and_version_precedence(self):
        files=self.files('trial1')+self.files('trial2','_auto')
        files.append(('files',('trial2_reviewed.TextGrid',self.grid.replace('三'.encode(),'五'.encode()),'text/plain')))
        r=self.post(files);self.assertEqual(r.status_code,200,r.text)
        rows=r.json()['project']['trials'];self.assertEqual(len(rows),2);self.assertEqual(rows[1]['corrected'],'五 四')
    def test_bad_batch_leaves_no_partial_project_or_input(self):
        bad=self.files('good')+self.files('bad')
        key,(name,_,typ)=bad[-1];bad[-1]=(key,(name,b'not a TextGrid',typ))
        r=self.post(bad);self.assertEqual(r.status_code,400,r.text)
        self.assertIn('bad.wav',r.json()['detail'])
        self.assertEqual(list(storage.DATA.glob('*/project.json')),[])
        self.assertEqual(list((storage.DATA/'inputs').iterdir()),[])
    def test_missing_files_duplicates_traversal_and_wrong_duration(self):
        for files in (self.files()[:2],self.files()+self.files(),[('files',('../escape.wav',self.wav,'audio/wav'))]):
            r=self.post(files);self.assertEqual(r.status_code,400,r.text)
        files=self.files();key,(name,_,typ)=files[-1]
        files[-1]=(key,(name,textgrid.serialize(self.intervals,2).encode(),typ))
        r=self.post(files);self.assertEqual(r.status_code,400);self.assertIn('音频不一致',r.json()['detail'])
        self.assertEqual(list(storage.DATA.glob('*/project.json')),[])
    def test_single_custom_interval_tier_supported(self):
        files=self.files();key,(name,body,typ)=files[-1]
        files[-1]=(key,(name,body.replace(b'name = "words"',b'name = "manual"'),typ))
        r=self.post(files);self.assertEqual(r.status_code,200,r.text)
    def test_managed_input_flag_does_not_allow_other_data_folders(self):
        invalid=storage.DATA/'other';invalid.mkdir(parents=True)
        with self.assertRaises(ValueError):storage.import_folder(str(invalid),'unknown',managed=True)

if __name__=='__main__':unittest.main()
