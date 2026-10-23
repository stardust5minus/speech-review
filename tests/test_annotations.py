import copy,csv,io,tempfile,unittest,wave,zipfile
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend import exports,storage
from backend.main import app

def trial(filename,labels,notes='',saved=True,condition='nonhomo'):
    return {'id':'1','filename':filename,'condition':condition,'saved':saved,'labels':labels,'notes':notes}

class SheetAnnotations(unittest.TestCase):
    def project(self,trials):return {'participant':'任意项目名称','trials':trials}
    def test_matches_sample_multiline_cell_and_actual_trial_number(self):
        p=self.project([trial('3nonhomo_001_trial26.wav',['disfluency'],'th'),trial('3nonhomo_001_trial11.wav',['disfluency'],'额')])
        before=copy.deepcopy(p);rows=exports.annotation_rows(p)
        self.assertEqual(rows,[{'participant':'001','annotation':'001 - trial11 - 额 - disfluency\n001 - trial26 - th - disfluency'}])
        parsed=list(csv.DictReader(io.StringIO(exports.annotation_csv(p).decode('utf-8-sig'))))
        self.assertEqual(parsed,rows);self.assertEqual(p,before)
    def test_multiple_labels_details_and_silence_count(self):
        p=self.project([trial('3nonhomo_015_trial7.wav',['silent']),trial('3nonhomo_015_trial5.wav',['silent']),trial('3nonhomo_015_trial8.wav',['self_correction','disfluency'],'额'),trial('3nonhomo_015_trial9.wav',['wrong_word'],'妈→马'),trial('3nonhomo_015_trial10.wav',['other'],'special drop')])
        text=exports.annotation_rows(p)[0]['annotation']
        self.assertIn('015 - trial8 - 额 - self correction + disfluency',text)
        self.assertIn('015 - trial9 - 妈→马 - wrong word/pronunciation',text)
        self.assertIn('015 - trial10 - special drop - other',text)
        self.assertTrue(text.endswith('2 silence'));self.assertEqual(len(p['trials']),5)
    def test_subjects_not_merged_and_leading_zeroes_preserved(self):
        p=self.project([trial('1number_010_trial1.wav',['self_correction']),trial('3nonhomo_003_trial18.wav',['wrong_word'],'课发成二声')])
        rows=exports.annotation_rows(p);self.assertEqual([r['participant'] for r in rows],['003','010'])
        self.assertIn('003 - trial18 - 课发成二声 - wrong word/pronunciation',rows[0]['annotation'])
    def test_unchecked_model_flags_and_unsaved_labels_excluded(self):
        p=self.project([trial('3nonhomo_001_trial1.wav',[]),trial('3nonhomo_001_trial2.wav',['disfluency'],saved=False)])
        p['trials'][0]['qc']={'issues':[{'type':'disfluency','text':'额'}]}
        self.assertEqual(exports.annotation_rows(p),[])
    def test_same_subject_multiple_conditions_keeps_one_row_without_ambiguous_trials(self):
        p=self.project([trial('1number_001_trial1.wav',['self_correction'],condition='number'),trial('3nonhomo_001_trial1.wav',['disfluency'])])
        rows=exports.annotation_rows(p);self.assertEqual(len(rows),1)
        self.assertIn('001 - number - trial1',rows[0]['annotation']);self.assertIn('001 - nonhomo - trial1',rows[0]['annotation'])
    def test_quotes_commas_unicode_and_fallback_names(self):
        p={'participant':'Subject 069','trials':[trial('trial09.wav',['wrong_word'],'妈→马, "额"')]}
        rows=exports.annotation_rows(p);self.assertEqual(rows[0]['participant'],'069');self.assertIn('trial9',rows[0]['annotation'])
        self.assertEqual(list(csv.DictReader(io.StringIO(exports.annotation_csv(p).decode('utf-8-sig')))),rows)
    def test_routes_and_all_data_zip(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(storage,'DATA',Path(temp)/'data'):
            source=Path(temp)/'001';source.mkdir()
            with wave.open(str(source/'1number_001_trial11.wav'),'wb') as w:w.setparams((1,2,16000,0,'NONE',''));w.writeframes(bytes(3200))
            p=storage.import_folder(str(source),'number');pid=p['id'];client=TestClient(app,base_url='http://127.0.0.1')
            self.assertEqual(client.get(f'/api/projects/{pid}/annotations').status_code,400)
            storage.save_review(pid,'1',{'corrected':'七 零','labels':['disfluency'],'notes':'额','complete':False})
            response=client.get(f'/api/projects/{pid}/annotations');self.assertEqual(response.status_code,200)
            self.assertIn('001 - trial11 - 额 - disfluency',response.content.decode('utf-8-sig'))
            self.assertEqual(client.get(f'/api/projects/{pid}/annotations?format=json').json()['participants'],1)
            self.assertEqual(client.get(f'/api/projects/{pid}/annotations?format=txt').text,'001 - trial11 - 额 - disfluency\n')
            self.assertEqual(client.get(f'/api/projects/{pid}/annotations?format=invalid').status_code,400)
            with zipfile.ZipFile(io.BytesIO(client.get(f'/api/projects/{pid}/export-everything').content)) as z:
                self.assertIn('annotations_sheet.csv',z.namelist());self.assertIn('annotations.txt',z.namelist())
    def test_label_only_save_does_not_accept_blank_transcript(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(storage,'DATA',Path(temp)/'data'):
            source=Path(temp)/'001';source.mkdir()
            with wave.open(str(source/'1number_001_trial11.wav'),'wb') as w:w.setparams((1,2,16000,0,'NONE',''));w.writeframes(bytes(3200))
            p=storage.import_folder(str(source),'number');pid=p['id'];client=TestClient(app,base_url='http://127.0.0.1')
            response=client.post(f'/api/projects/{pid}/save-all',json={'trials':[{'id':'1','corrected':'','labels':['disfluency'],'notes':'额','complete':False,'annotation_only':True}]})
            self.assertEqual(response.status_code,200)
            t=storage.trial(storage.read(pid),'1');self.assertFalse(t['saved']);self.assertIsNone(t['corrected']);self.assertTrue(t['annotations_saved'])
            self.assertFalse((storage.DATA/pid/'corrected').exists())
            self.assertIn('001 - trial11 - 额 - disfluency',client.get(f'/api/projects/{pid}/annotations').text)

if __name__=='__main__':unittest.main()
