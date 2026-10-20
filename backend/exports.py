import csv
import io
import zipfile

def export_zip(project):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for t in project['trials']:
            if t['saved']:
                z.writestr(t['txt_name'],t['corrected']+'\n')
    return out.getvalue()

def report(project):
    out=io.StringIO(newline='')
    fields=['participant','condition','filename','saved','complete','labels','notes','original_transcript','raw_model_transcription','corrected_transcription','model_issues']
    w=csv.DictWriter(out,fieldnames=fields); w.writeheader()
    for t in project['trials']:
        w.writerow({'participant':project['participant'],**{k:t[k] for k in ('condition','filename','saved','complete','notes')},'labels':' | '.join(t['labels']),'original_transcript':t['original'], 'raw_model_transcription':(t['asr'] or {}).get('raw'),'corrected_transcription':t['corrected'],'model_issues':' | '.join(i['text'] for i in (t['qc'] or {}).get('issues',[]))})
    return ('\ufeff'+out.getvalue()).encode('utf-8')
