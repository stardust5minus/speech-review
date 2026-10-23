import csv
import io
import zipfile
import re
from pathlib import Path

ANNOTATION_LABELS={'self_correction':'self correction','silent':'silence','disfluency':'disfluency','wrong_word':'wrong word/pronunciation','other':'other'}

def annotation_identity(project,trial):
    stem=Path(trial['filename']).stem
    speaker=re.search(r'(?:nonhomo|homo|number)[ _-]+(\d+)',stem,re.I)
    if not speaker:speaker=re.match(r'(\d+)[ _-]+(?:trial|trail)',stem,re.I)
    fallback=re.fullmatch(r'(?:(?:subject|participant|sub|受试者)[ _-]*)?(\d+)',project['participant'],re.I)
    participant=speaker.group(1) if speaker else fallback.group(1) if fallback else project['participant']
    if participant.isdigit():participant=participant.zfill(3)
    number=re.search(r'(?:trial|trail)[ _-]*(\d+)',stem,re.I)
    return participant,str(int(number.group(1))) if number else trial['id']

def annotation_rows(project):
    grouped={}
    for trial in project['trials']:
        labels=[key for key in ANNOTATION_LABELS if key in trial.get('labels',[])]
        if not (trial.get('saved') or trial.get('annotations_saved')) or not labels:continue
        participant,number=annotation_identity(project,trial)
        grouped.setdefault(participant,[]).append({'trial':number,'condition':trial.get('condition','unknown'),'labels':labels,'notes':' '.join(trial.get('notes','').split())})
    rows=[]
    for participant,items in sorted(grouped.items(),key=lambda pair:(not pair[0].isdigit(),int(pair[0]) if pair[0].isdigit() else pair[0])):
        conditions={i['condition'] for i in items}
        lines=[]
        for item in sorted(items,key=lambda i:(int(i['trial']) if i['trial'].isdigit() else 10**9,i['condition'])):
            parts=[participant]
            if len(conditions)>1:parts.append(item['condition'])
            parts.append('trial'+item['trial'])
            if item['notes']:parts.append(item['notes'])
            parts.append(' + '.join(ANNOTATION_LABELS[key] for key in item['labels']))
            lines.append(' - '.join(parts))
        silence=sum('silent' in item['labels'] for item in items)
        if silence:lines.append(f'{silence} silence')
        rows.append({'participant':participant,'annotation':'\n'.join(lines)})
    return rows

def annotation_csv(project):
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=['participant','annotation']);writer.writeheader();writer.writerows(annotation_rows(project))
    return ('\ufeff'+out.getvalue()).encode('utf-8')

def annotation_text(project):
    return ('\n\n'.join(row['annotation'] for row in annotation_rows(project))+'\n').encode('utf-8')

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
