import {useLanguage} from '../i18n';
import React, { useState, useRef, useEffect } from 'react';
import Waveform from './Waveform';
import { api } from '../api';
import AlignmentEditor from './AlignmentEditor';
export const LABELS = { self_correction: '自我纠正', silent: '静音', disfluency: '不流畅', wrong_word: '错词／发音待核查', other: '其他' };
export default function TrialCard({ trial: t, pid, onSaved, onTranscribe, busy, active, onDirty, alignBusy, onAlign, onRefresh, register, alignmentOnly = false, playerVisible = true }) {
    const { tr } = useLanguage();
    const player = useRef();
    const [overlay, setOverlay] = useState({ intervals: [], editable: false });
    const [draft, setDraft] = useState(t.corrected ?? ''), [labels, setLabels] = useState(t.labels), [notes, setNotes] = useState(t.notes), [complete, setComplete] = useState(t.complete), [dirty, setDirty] = useState(false), [saving, setSaving] = useState(false), [message, setMessage] = useState('');
    const [version, setVersion] = useState(t.asr);
    const latestReview = useRef();
    latestReview.current = { payload: { corrected: draft, labels, notes, complete }, eligible: !!(draft.trim() || t.saved || t.asr || labels.includes('silent')) };
    useEffect(() => { if (!register)
        return; register(t.id, { snapshot: () => latestReview.current, acknowledge: payload => { if (JSON.stringify(latestReview.current.payload) === JSON.stringify(payload)) {
            setDirty(false);
            onDirty(t.id, false);
            setMessage(tr("\u5DF2\u4FDD\u5B58"));
        }
        else
            setMessage(tr("\u5DF2\u4FDD\u5B58\u63D0\u4EA4\u65F6\u7684\u7248\u672C\uFF0C\u5F53\u524D\u4FEE\u6539\u4ECD\u9700\u4FDD\u5B58")); } }); return () => register(t.id, null); }, [register, t.id]);
    const previousCorrected = useRef(t.corrected);
    useEffect(() => { if (previousCorrected.current !== t.corrected && !dirty)
        setDraft(t.corrected ?? ''); previousCorrected.current = t.corrected; }, [t.corrected, dirty]);
    if (version !== t.asr) {
        setVersion(t.asr);
        if (!dirty)
            setDraft(t.corrected ?? '');
    }
    function change(fn) { fn(); setDirty(true); onDirty(t.id, true); setMessage(''); }
    async function save() { setSaving(true); try {
        const row = await api(`/projects/${pid}/trials/${t.id}`, 'PUT', { corrected: draft, labels, notes, complete });
        setDirty(false);
        onDirty(t.id, false);
        setMessage(tr("\u5DF2\u4FDD\u5B58"));
        onSaved(row);
    }
    catch (e) {
        setMessage(e.message);
    }
    finally {
        setSaving(false);
    } }
    return <article className={'trial ' + (t.complete ? 'completed' : '')}>
 <div className="trial-header"><h2><span className="number">#{t.id.padStart(3, '0')}</span> · {t.filename}</h2><span className="badge">{t.condition === 'unknown' ? tr("\u6761\u4EF6\u672A\u6307\u5B9A") : t.condition} · {t.complete ? tr("\u5DF2\u5B8C\u6210") : tr("\u5F85\u590D\u542C")}</span></div>
 <Waveform url={`/api/projects/${pid}/trials/${t.id}/audio`} {...overlay} height={alignmentOnly ? 170 : 88} visible={playerVisible} onReady={ws => { player.current = ws; }}/>
 {alignmentOnly && <p className="alignment-transcript"><b>{tr("\u5DF2\u4FDD\u5B58\u4FEE\u8BA2\u6587\u672C\uFF1A")}</b>{t.saved ? t.corrected : tr("\u5C1A\u672A\u4FDD\u5B58\uFF0C\u8BF7\u5148\u5728\u201C\u8F6C\u5199\u4E0E\u590D\u542C\u201D\u4E2D\u4FDD\u5B58 TXT\u3002")}</p>}
 <div hidden={alignmentOnly}>
 <details className="model" open><summary>{tr("\u6A21\u578B\u8F6C\u5199\u4E0E\u8BCA\u65AD")}<span>Whisper · {t.condition}</span></summary><p className="transcript">{t.asr ? t.asr.raw || tr("\uFF08\u6A21\u578B\u672A\u8BC6\u522B\u5230\u6587\u5B57\uFF09") : tr("\u5C1A\u672A\u8F6C\u5199")}</p>
 {t.asr && t.asr.pipeline_version !== 'notebook-v1' && <p className="error">{tr("\u8FD9\u662F\u65E7\u7248\u901A\u7528\u6D41\u7A0B\u7684\u7ED3\u679C\u3002\u8BF7\u6309\u539F notebook \u91CD\u65B0\u8F6C\u5199\u3002")}</p>}
 {t.qc?.notebook_result !== undefined && <section className="notebook-result"><b>{tr("\u539F\u811A\u672C\u5904\u7406\u7ED3\u679C \u00B7 \u5C1A\u672A\u91C7\u7528")}</b><p className="transcript">{t.qc.notebook_result || tr("\uFF08\u539F\u811A\u672C\u5904\u7406\u540E\u4E3A\u7A7A\uFF09")}</p>{t.qc.notebook_duplicate && <p className="error">{tr("\u6B64\u7ED3\u679C\u5305\u542B\u539F\u811A\u672C\u7684\u91CD\u590D\u5220\u9664\uFF0C\u8BF7\u5148\u6838\u5BF9\u97F3\u9891\u3002")}</p>}<button disabled={busy} onClick={() => change(() => setDraft(t.qc.notebook_result))}>{tr("\u91C7\u7528\u811A\u672C\u7ED3\u679C\u5230\u590D\u542C\u7ED3\u8BBA")}</button><small>{tr("\u70B9\u51FB\u540E\u4ECD\u9700 Save\uFF1B\u539F\u59CB\u8F6C\u5199\u4FDD\u7559")}</small></section>}
 {t.asr?.parameters && <details><summary>{tr("\u8FD0\u884C\u914D\u7F6E \u00B7 \u539F notebook")}</summary><p>{t.asr.profile} · {t.asr.model} · {t.asr.device} · {t.asr.compute_type}</p><p className="transcript">{t.asr.parameters.initial_prompt}</p><pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify({ ...t.asr.parameters, initial_prompt: undefined }, null, 2)}</pre></details>}
 <div className="flags">{t.qc?.issues.map((i, k) => <p key={k}>⚠ {tr(i.text)}</p>)}</div><button className="subtle" disabled={busy || dirty} onClick={() => onTranscribe(t.id)}>{active ? tr("\u6B63\u5728\u8F6C\u5199\u2026") : busy ? tr("\u4EFB\u52A1\u8FD0\u884C\u4E2D") : t.asr ? tr("\u91CD\u65B0\u8F6C\u5199") : tr("\u8FD0\u884C Whisper")}</button>{dirty && <small>{tr("\u5148\u4FDD\u5B58\u5F53\u524D\u4FEE\u6539\uFF0C\u518D\u91CD\u65B0\u8F6C\u5199")}</small>}</details>
 <details className="reference"><summary>{tr("\u539F\u6765\u7684 TXT \u00B7 \u53C2\u8003\u5907\u4EFD")}</summary><p className="transcript">{t.original ?? tr("\u672A\u627E\u5230\u540C\u540D TXT")}</p></details>
 <label className="editor-label" htmlFor={'edit' + t.id}>{tr("\u590D\u542C\u7ED3\u8BBA")}<small>{tr("\u9996\u6B21\u9884\u586B Whisper \u6587\u5B57\uFF0C\u4FDD\u7559\u91CD\u590D\u548C\u586B\u5145\u8BCD")}</small></label>
 <div className="editor"><textarea id={'edit' + t.id} rows="2" placeholder={tr("\u7B49\u5F85 Whisper \u8F6C\u5199\uFF0C\u6216\u76F4\u63A5\u8F93\u5165\u5B9E\u9645\u542C\u5230\u7684\u5185\u5BB9\u2026")} value={draft} onChange={e => change(() => setDraft(e.target.value))}/><button className="primary" disabled={saving} onClick={save}>{saving ? tr("\u4FDD\u5B58\u4E2D\u2026") : 'Save'}</button></div>
 <p className="hint">{tr("\u4EBA\u5DE5\u6807\u6CE8\uFF08\u53EF\u591A\u9009\uFF09\uFF1A\u5177\u4F53\u95EE\u9898\u5199\u5728\u4E0B\u65B9\u5907\u6CE8\uFF0C\u9876\u90E8\u53EF\u4E00\u952E\u5BFC\u51FA Sheet \u683C\u5F0F\u3002")}</p><div className="manual">{Object.entries(LABELS).map(([key, label]) => <label key={key}><input type="checkbox" checked={labels.includes(key)} onChange={e => change(() => setLabels(e.target.checked ? [...labels, key] : labels.filter(x => x !== key)))}/>{tr(label)}</label>)}</div>
 <div className="bottom"><input className="notes" aria-label={tr("\u5907\u6CE8")} placeholder={tr("\u6807\u6CE8\u8BE6\u60C5\uFF0F\u5907\u6CE8\uFF1A\u4F8B\u5982 \u989D\u3001\u5988\u2192\u9A6C\u3001\u8BFE\u53D1\u6210\u4E8C\u58F0\uFF08\u7528\u4E8E\u6807\u6CE8\u5BFC\u51FA\uFF0C\u4E0D\u5199\u5165\u8F6C\u5199 TXT\uFF09")} value={notes} onChange={e => change(() => setNotes(e.target.value))}/><label><input type="checkbox" checked={complete} onChange={e => change(() => setComplete(e.target.checked))}/>{tr("\u6807\u8BB0\u5B8C\u6210")}</label><span role="status" className={dirty ? 'unsaved' : 'saved'}>{dirty ? tr("\u6709\u672A\u4FDD\u5B58\u4FEE\u6539") : tr(message) || (t.saved ? tr("\u5DF2\u4FDD\u5B58") : tr("\u5C1A\u672A\u4FDD\u5B58"))}</span></div>
 </div>
 <AlignmentEditor trial={t} pid={pid} disabled={busy || dirty} alignBusy={alignBusy} onStart={onAlign} onOverlay={setOverlay} onDirty={value => onDirty('alignment-' + t.id, value)} onChanged={onRefresh} play={(start, end) => player.current?.play(start, end)}/>
 </article>;
}
