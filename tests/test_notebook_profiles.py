import ast
import json
import unittest
from pathlib import Path
from backend import profiles
from backend.notebook_code import number,homo,nonhomo

class NotebookProfiles(unittest.TestCase):
    def test_original_prompts_and_parameters(self):
        self.assertEqual(profiles.parameters('number'),{'language':'zh','vad_filter':True,'initial_prompt':number.PROMPT})
        self.assertEqual(profiles.parameters('homo')['initial_prompt'],homo.PROMPT)
        self.assertEqual(profiles.parameters('homo')['best_of'],5)
        self.assertNotIn('best_of',profiles.parameters('nonhomo'))
        self.assertEqual(profiles.parameters('nonhomo')['initial_prompt'],nonhomo.PROMPT)
    def test_number_tokenization_and_original_rule(self):
        result=profiles.analyze('七零八一四十九五六','number')
        self.assertEqual(result['spaced'],'七 零 八 一 四 十 九 五 六')
        self.assertEqual(result['notebook_result'],result['spaced'])
        self.assertTrue(result['notebook_flags']['self_correction'])
        self.assertEqual(number.tokenize_zh('708'),'7 0 8'.split())
        self.assertEqual(profiles.infer_condition('1number_088_trial1.wav'),'number')
        self.assertEqual(profiles.infer_condition('3nonhomo_088_trial1.wav'),'nonhomo')
    def test_homo_mapping_separate(self):
        result=profiles.analyze('零 一 四 五 六 七 八 九 十','homo')
        self.assertEqual(result['spaced'],'零 一 四 五 六 七 八 九 十')
        self.assertEqual(result['notebook_result'],'铃 衣 寺 舞 遛 妻 疤 酒 石')
    def test_nonhomo_exact_script_output_separate(self):
        raw='指 课 指'
        result=profiles.analyze(raw,'nonhomo')
        tokens=nonhomo.normalize_tokens(nonhomo.tokenize_zh(nonhomo.preprocess_raw(raw)))
        exact,duplicate=nonhomo.deduplicate(tokens)
        self.assertEqual(result['notebook_result'],' '.join(exact))
        self.assertEqual(result['spaced'],'指 课 指')
        self.assertTrue(duplicate)
    def test_extracted_code_provenance(self):
        # Verify generated manifest is present in the deliverable.
        manifest=json.loads((Path(profiles.__file__).parent/'notebook_code'/'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['profiles']['number']['cell_index'],9)
        self.assertEqual(manifest['profiles']['homo']['cell_index'],18)
        self.assertEqual(manifest['profiles']['nonhomo']['cell_index'],19)
    def test_number_parameters_reach_model_unchanged(self):
        import types
        import numpy as np
        from unittest.mock import patch,MagicMock
        from backend import transcription
        model=MagicMock()
        model.transcribe.return_value=(iter([types.SimpleNamespace(text=' 七零八 ',start=0,end=1,avg_logprob=-.3)]),None)
        with patch.dict(transcription._models,{'number':(model,'medium','cpu','int8')},clear=True),patch.object(transcription,'decode_audio',return_value=np.zeros(16000,dtype=np.float32)):
            result=transcription.transcribe('1number_test.wav',condition='number')
        self.assertEqual(model.transcribe.call_args.kwargs,profiles.parameters('number'))
        self.assertEqual(result['notebook_raw'],'七零八')
        self.assertEqual(result['raw'],' 七零八 ')
        self.assertEqual(result['profile'],'number')

if __name__=='__main__':unittest.main()
