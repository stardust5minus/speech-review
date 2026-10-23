import io
import json
import tempfile
import time
import unittest
import wave
import zipfile
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend import storage,alignment,textgrid
from backend.main import app

class AlignmentFlow(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.patch=patch.object(storage,'DATA',self.root/'data');self.patch.start()
        source=self.root/'029';source.mkdir();self.wav=source/'trial1.wav'
        with wave.open(str(self.wav),'wb') as w:w.setparams((1,2,16000,0,'NONE',''));w.writeframes(bytes(32000))
        p=storage.import_folder(str(source),'number');self.pid=p['id'];self.tid='1'
        storage.save_review(self.pid,'1',{'corrected':'三 呃 四','labels':[],'notes':'','complete':True})
        storage.update(self.pid,'1',lambda t:t.update(asr={'raw':'绝对不用于对齐'}))
        self.client=TestClient(app,base_url='http://127.0.0.1')
        self.words=[{'text':'三','start':.1,'end':.25},{'text':'呃','start':.4,'end':.5},{'text':'四','start':.7,'end':.9}]
    def tearDown(self):self.patch.stop();self.tmp.cleanup()
    def fake_mfa(self,args,log_path,timeout=1800):
        self.assertEqual(args[0],'align')
        self.assertEqual((Path(args[1])/'input.lab').read_text(encoding='utf-8'),'三 呃 四\n')
        self.assertIn('--no_tokenization',args)
        out=Path(args[4]);out.mkdir()
        (out/'input.TextGrid').write_text(textgrid.serialize(self.words,1),encoding='utf-8')
    def auto(self):
        jid='test-align-'+str(time.time_ns())
        alignment.jobs[jid]={'project_id':self.pid,'started_at':time.time(),'status':'running','done':0,'total':1,'errors':[]}
        with patch('backend.mfa_runtime.ensure_models'),patch('backend.mfa_runtime.run',side_effect=self.fake_mfa):
            alignment.run_job(jid,self.pid,['1'])
        self.assertEqual(alignment.jobs[jid]['errors'],[])
        return alignment.view(self.pid,'1')['auto']
    def review(self,base,words=None):
        return self.client.put(f'/api/projects/{self.pid}/trials/1/alignment',json={'intervals':words or base['intervals'],'transcript':base['transcript'],'base_id':base['id']})
    def test_real_textgrid_roundtrip_and_silence(self):
        path=self.root/'valid.TextGrid';path.write_text(textgrid.serialize(self.words,1),encoding='utf-8')
        self.assertEqual(textgrid.parse(path,1,'三 呃 四'),self.words)
        from praatio import textgrid as praat
        grid=praat.openTextgrid(str(path),includeEmptyIntervals=True)
        self.assertEqual(grid.maxTimestamp,1)
        entries=grid.getTier('words').entries
        self.assertEqual(entries[0].label,'');self.assertEqual(entries[-1].label,'')
        for left,right in zip(entries,entries[1:]):self.assertAlmostEqual(left.end,right.start)
    def test_manual_preserved_after_rerun_and_txt_stale(self):
        base=self.auto();words=[dict(i) for i in self.words];words[0]['end']=.3
        r=self.review(base,words);self.assertEqual(r.status_code,200,r.text);reviewed=r.json()['reviewed']
        newer=self.auto();self.assertNotEqual(base['id'],newer['id'])
        self.assertEqual(alignment.view(self.pid,'1')['reviewed']['id'],reviewed['id'])
        downloaded=self.client.get(f'/api/projects/{self.pid}/trials/1/textgrid?version=reviewed')
        self.assertEqual(downloaded.status_code,200)
        self.assertIn('trial1_reviewed.TextGrid',downloaded.headers['content-disposition'])
        self.assertIn('Object class = "TextGrid"',downloaded.text)
        storage.save_review(self.pid,'1',{'corrected':'三 四','labels':[],'notes':'','complete':True})
        self.assertTrue(alignment.view(self.pid,'1')['reviewed']['stale'])
        self.assertEqual(self.client.get(f'/api/projects/{self.pid}/trials/1/textgrid?version=reviewed').status_code,400)
        self.assertEqual(self.client.get(f'/api/projects/{self.pid}/textgrids').status_code,400)
    def test_reset_archives_reviewed_only_after_success(self):
        base=self.auto();reviewed=self.review(base).json()['reviewed']
        jid='reset-'+str(time.time_ns())
        alignment.jobs[jid]={'project_id':self.pid,'started_at':time.time(),'status':'running','done':0,'total':1,'errors':[], 'reset_reviewed':True,'expected_reviewed_id':reviewed['id']}
        with patch('backend.mfa_runtime.ensure_models'),patch('backend.mfa_runtime.run',side_effect=RuntimeError('MFA failed')):
            alignment.run_job(jid,self.pid,['1'])
        self.assertEqual(alignment.view(self.pid,'1')['reviewed']['id'],reviewed['id'])
        alignment.jobs[jid].update(errors=[],done=0,status='running')
        with patch('backend.mfa_runtime.ensure_models'),patch('backend.mfa_runtime.run',side_effect=self.fake_mfa):
            alignment.run_job(jid,self.pid,['1'])
        self.assertEqual(alignment.jobs[jid]['errors'],[])
        result=alignment.view(self.pid,'1')
        self.assertIsNone(result['reviewed'])
        self.assertNotEqual(result['auto']['id'],base['id'])
        trial=storage.trial(storage.read(self.pid),'1')
        self.assertTrue(any(h['id']==reviewed['id'] and h.get('archived_reason')=='MFA reset' for h in trial['alignment_history']))

    def test_reset_rejects_concurrent_manual_save(self):
        base=self.auto();reviewed=self.review(base).json()['reviewed']
        latest=self.review(base).json()['reviewed']
        record=alignment.make_record(storage.trial(storage.read(self.pid),'1'),self.words,1,'MFA')
        with self.assertRaises(ValueError):
            alignment.save_version(self.pid,'1','auto',record,reset_reviewed=True,expected_reviewed_id=reviewed['id'])
        result=alignment.view(self.pid,'1')
        self.assertEqual(result['reviewed']['id'],latest['id'])
        self.assertEqual(result['auto']['id'],base['id'])

    def test_invalid_edits_rejected_without_overwrite(self):
        base=self.auto()
        for start,end in [(-1,.2),(.3,.2),(.1,1.5),(.1,.45)]:
            words=[dict(i) for i in self.words];words[0].update(start=start,end=end)
            self.assertEqual(self.review(base,words).status_code,400)
        self.assertIsNone(alignment.view(self.pid,'1')['reviewed'])
        with self.assertRaises(ValueError):textgrid.validate([{'start':float('nan'),'end':1,'text':'三'}],1)
    def test_import_reviewed_and_export_everything(self):
        content=textgrid.serialize(self.words,1)
        r=self.client.post(f'/api/projects/{self.pid}/trials/1/alignment/import',json={'content':content})
        self.assertEqual(r.status_code,200,r.text)
        first=r.json()['reviewed']['id']
        self.client.post(f'/api/projects/{self.pid}/trials/1/alignment/import',json={'content':content})
        t=storage.trial(storage.read(self.pid),'1');self.assertEqual(t['alignment_history'][0]['id'],first)
        data=self.client.get(f'/api/projects/{self.pid}/export-everything')
        with zipfile.ZipFile(io.BytesIO(data.content)) as z:
            self.assertIn('corrected_txt/trial1.txt',z.namelist())
            self.assertIn('textgrids/trial1_reviewed.TextGrid',z.namelist())
            self.assertIn('report.csv',z.namelist());self.assertIn('alignment.csv',z.namelist())
            self.assertEqual(z.read('corrected_txt/trial1.txt').decode(),'三 呃 四\n')
    def test_mismatched_words_never_accepted(self):
        bad=[{'text':'三','start':.1,'end':.3},{'text':'四','start':.7,'end':.9}]
        content=textgrid.serialize(bad,1)
        r=self.client.post(f'/api/projects/{self.pid}/trials/1/alignment/import',json={'content':content})
        self.assertEqual(r.status_code,400)
        self.assertIn('不一致',r.json()['detail'])
        self.assertIsNone(alignment.view(self.pid,'1')['reviewed'])
    def test_edit_labels_split_empty_intervals_and_export_plain_names(self):
        base=self.auto()
        words=[{'text':'三 呃','start':0,'end':.4},{'text':'新增','start':.4,'end':.6},{'text':'','start':.6,'end':.7},{'text':'四','start':.7,'end':1}]
        response=self.client.put(f'/api/projects/{self.pid}/trials/1/alignment',json={'intervals':words,'transcript':base['transcript'],'base_id':base['id'],'update_transcript':True})
        self.assertEqual(response.status_code,200,response.text)
        row=storage.trial(storage.read(self.pid),'1')
        self.assertEqual(row['corrected'],'三 呃 新增 四')
        self.assertEqual(row['asr']['raw'],'绝对不用于对齐')
        self.assertEqual(row['history'][-1]['corrected'],'三 呃 四')
        self.assertEqual((storage.DATA/self.pid/'corrected'/'trial1.txt').read_text(encoding='utf-8'),'三 呃 新增 四\n')
        self.assertTrue(alignment.view(self.pid,'1')['auto']['stale'])
        self.assertFalse(alignment.view(self.pid,'1')['reviewed']['stale'])
        with zipfile.ZipFile(io.BytesIO(self.client.get(f'/api/projects/{self.pid}/reviewed-textgrids').content)) as z:
            self.assertEqual(z.namelist(),['trial1.TextGrid'])
            path=self.root/'manual.TextGrid';path.write_bytes(z.read('trial1.TextGrid'))
            self.assertEqual(textgrid.parse(path,1,row['corrected'],manual=True),words)
        stale=self.client.put(f'/api/projects/{self.pid}/trials/1/alignment',json={'intervals':words,'transcript':base['transcript'],'base_id':base['id'],'update_transcript':True})
        self.assertEqual(stale.status_code,400)
        storage.save_review(self.pid,'1',{'corrected':'新 文字','labels':[],'notes':'','complete':True})
        self.assertEqual(self.client.get(f'/api/projects/{self.pid}/reviewed-textgrids').status_code,400)
    def test_plain_named_export_never_falls_back_to_auto(self):
        base=self.auto()
        self.assertEqual(self.client.get(f'/api/projects/{self.pid}/reviewed-textgrids').status_code,400)
        self.review(base)
        storage.update(self.pid,'1',lambda t:t.update(filename='3nonhomo_069_trial9.wav'))
        response=self.client.get(f'/api/projects/{self.pid}/reviewed-textgrids')
        self.assertEqual(response.status_code,200)
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:self.assertEqual(z.namelist(),['3nonhomo_069_trial9.TextGrid'])
    def test_invalid_label_edit_preserves_txt_and_previous_grid(self):
        base=self.auto();words=[{'text':'替换','start':.1,'end':2}]
        response=self.client.put(f'/api/projects/{self.pid}/trials/1/alignment',json={'intervals':words,'transcript':base['transcript'],'base_id':base['id'],'update_transcript':True})
        self.assertEqual(response.status_code,400)
        self.assertEqual(storage.trial(storage.read(self.pid),'1')['corrected'],'三 呃 四')
        self.assertIsNone(alignment.view(self.pid,'1')['reviewed'])
    def test_batch_shares_one_mfa_invocation(self):
        import copy,shutil
        p=storage.read(self.pid);second=copy.deepcopy(p['trials'][0]);second.update(id='2',filename='trial2.wav',txt_name='trial2.txt',audio_path=str(self.wav.with_name('trial2.wav')))
        shutil.copyfile(self.wav,second['audio_path']);p['trials'].append(second);storage.write(p)
        def fake(args,log_path):
            out=Path(args[4]);out.mkdir()
            for tid in ('1','2'):
                self.assertEqual((Path(args[1])/f'input_{tid}.lab').read_text(encoding='utf-8'),'三 呃 四\n')
                (out/f'input_{tid}.TextGrid').write_text(textgrid.serialize(self.words,1),encoding='utf-8')
        jid='test-batch-'+str(time.time_ns());alignment.jobs[jid]={'project_id':self.pid,'started_at':time.time(),'status':'running','done':0,'total':2,'errors':[]}
        with patch('backend.mfa_runtime.ensure_models'),patch('backend.mfa_runtime.run',side_effect=fake) as run:
            alignment.run_job(jid,self.pid,['1','2'])
        self.assertEqual(run.call_count,1)
        self.assertEqual(alignment.jobs[jid]['errors'],[])
        self.assertEqual(alignment.jobs[jid]['done'],2)
        self.assertIsNotNone(alignment.view(self.pid,'2')['auto'])

if __name__=='__main__':unittest.main()
