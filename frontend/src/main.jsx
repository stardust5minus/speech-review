import {useLanguage} from './i18n';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { api } from './api';
import TrialCard, { LABELS } from './components/TrialCard';
import './style.css';
import AlignmentPanel from './components/AlignmentPanel';
import ExistingImport from './components/ExistingImport';
import AnnotationExport from './components/AnnotationExport';
function App() {
    const { tr, language, setLanguage } = useLanguage();
    const [uploading, setUploading] = useState(false);
    const [project, setProject] = useState(null), [projects, setProjects] = useState([]), [folder, setFolder] = useState(''), [condition, setCondition] = useState('unknown'), [filter, setFilter] = useState('all'), [error, setError] = useState(''), [job, setJob] = useState(null), [loading, setLoading] = useState(false), [starting, setStarting] = useState(false);
    const dirty = useRef(new Set());
    const reviewHandles = useRef(new Map());
    const registerReview = useCallback((id, handle) => { if (handle)
        reviewHandles.current.set(id, handle);
    else
        reviewHandles.current.delete(id); }, []);
    const [savingAll, setSavingAll] = useState(false), [saveNotice, setSaveNotice] = useState('');
    const [view, setView] = useState(() => new URLSearchParams(location.search).get('view') === 'alignment' ? 'alignment' : 'transcription');
    const [selectedTrial, setSelectedTrial] = useState('1');
    function switchView(next) { setView(next); const url = new URL(location.href); url.searchParams.set('view', next); history.replaceState(null, '', url); }
    const alignStart = useRef();
    const [alignBusy, setAlignBusy] = useState(false);
    useEffect(() => { api('/projects').then(async (list) => { setProjects(list); let previous = null; try {
        previous = localStorage.getItem('speech-review-project');
    }
    catch { } ; const selected = list.find(p => p.id === previous) ?? (list.length === 1 ? list[0] : null); if (selected) {
        setProject(await api('/projects/' + selected.id));
        setJob(await api('/projects/' + selected.id + '/job'));
    } }).catch(e => setError(e.message)); const stop = e => { if (dirty.current.size) {
        e.preventDefault();
        e.returnValue = '';
    } }; window.addEventListener('beforeunload', stop); return () => window.removeEventListener('beforeunload', stop); }, []);
    useEffect(() => { if (project) {
        try {
            localStorage.setItem('speech-review-project', project.id);
        }
        catch { }
        ;
        setSelectedTrial('1');
    } }, [project?.id]);
    useEffect(() => { if (!job?.id || job.status !== 'running')
        return; const timer = setInterval(async () => { try {
        const j = await api('/jobs/' + job.id);
        setJob({ ...j, id: job.id });
        const fresh = await api('/projects/' + project.id);
        setProject(old => ({ ...fresh, trials: fresh.trials.map(t => { const prev = old.trials.find(p => p.id === t.id); return JSON.stringify(prev) === JSON.stringify(t) ? prev : t; }) }));
        if (j.errors.length)
            setError(j.errors.map(e => `#${e.trial}: ${e.message}`).join('\n'));
    }
    catch (e) {
        setJob(null);
        setError(tr("\u8F6C\u5199\u4EFB\u52A1\u8FDE\u63A5\u5DF2\u4E2D\u65AD\uFF1B\u5DF2\u4FDD\u5B58\u5185\u5BB9\u4FDD\u7559\u3002\u8BF7\u91CD\u65B0\u8FD0\u884C\u672A\u5904\u7406\u5F55\u97F3\u3002 ") + e.message);
    } }, 1200); return () => clearInterval(timer); }, [job?.id, job?.status, project?.id]);
    function nextAlignment(id) { const index = project.trials.findIndex(t => t.id === id); const next = project.trials[index + 1]; if (index < 0 || !next) return false; setSelectedTrial(next.id); requestAnimationFrame(() => { const wave = document.getElementById('trial-card-' + next.id)?.querySelector('.wave'); wave?.focus({preventScroll:true}); wave?.scrollIntoView({block:'center',behavior:'smooth'}); }); return true; }
    async function refreshProject() { const fresh = await api('/projects/' + project.id); setProject(old => ({ ...fresh, trials: fresh.trials.map(t => { const prev = old.trials.find(p => p.id === t.id); return JSON.stringify(prev) === JSON.stringify(t) ? prev : t; }) })); }
    function unsaved() { if (dirty.current.size) {
        setError(tr("\u8BF7\u5148 Save \u6240\u6709\u4FEE\u6539\uFF0C\u518D\u5207\u6362\u9879\u76EE\u6216\u6279\u91CF\u8F6C\u5199\u3002"));
        return true;
    } return false; }
    async function open(id) { if (unsaved())
        return; setError(''); try {
        setProject(await api('/projects/' + id));
        setJob(await api('/projects/' + id + '/job'));
        setFilter('all');
    }
    catch (e) {
        setError(e.message);
    } }
    async function importedExisting(p) { setProjects(await api('/projects')); setProject(p); setJob(null); setFilter('all'); setError(''); setSaveNotice(''); switchView('alignment'); }
    async function load() { if (unsaved())
        return; setLoading(true); setError(''); try {
        const p = await api('/import', 'POST', { folder, condition });
        setProject(p);
        setJob(await api('/projects/' + p.id + '/job'));
        setProjects(await api('/projects'));
        setFilter('all');
    }
    catch (e) {
        setError(e.message);
    }
    finally {
        setLoading(false);
    } }
    async function saveAll(options) { const annotationExport = options?.annotations === true; if (!project)
        return false; setSavingAll(true); setError(''); setSaveNotice(''); const payloads = project.trials.flatMap(t => { const entry = reviewHandles.current.get(t.id)?.snapshot(); return entry && (entry.eligible || annotationExport && (entry.payload.labels.length || entry.payload.notes.trim())) ? [{ id: t.id, ...entry.payload, annotation_only: annotationExport && !t.saved && !t.asr && !entry.payload.corrected.trim() && !entry.payload.labels.includes('silent') }] : []; }); try {
        if (!payloads.length)
            throw Error(tr("\u6682\u65E0\u53EF\u4FDD\u5B58\u7684\u8F6C\u5199\uFF0C\u8BF7\u5148\u8FD0\u884C Whisper \u6216\u8F93\u5165\u6587\u5B57\u3002"));
        const result = await api(`/projects/${project.id}/save-all`, 'POST', { trials: payloads });
        const sent = new Map(payloads.map(({ id, annotation_only, ...payload }) => [id, payload]));
        for (const row of result.saved)
            reviewHandles.current.get(row.id)?.acknowledge(sent.get(row.id));
        setProject(p => ({ ...p, trials: p.trials.map(t => result.saved.find(r => r.id === t.id) ?? t) }));
        setSaveNotice(annotationExport ? tr("\u5DF2\u4FDD\u5B58\u5F53\u524D\u4EBA\u5DE5\u6807\u6CE8\u4E0E\u5907\u6CE8\u3002") : tr("\u5DF2\u4FDD\u5B58 {0} / {1} \u6761 TXT\uFF1B\u8DF3\u8FC7\u672A\u8F6C\u5199\u4E14\u65E0\u6587\u5B57\u7684 {2} \u6761\u3002\u6587\u4EF6\u540D\u4E0E\u539F TXT \u4E00\u81F4\u3002", [result.saved.length, project.trials.length, project.trials.length - payloads.length]));
        if (result.errors.length)
            setError(result.errors.map(e => `#${e.trial}：${e.message}`).join('\n'));
        return result.errors.length === 0;
    }
    catch (e) {
        setError(e.message);
        return false;
    }
    finally {
        setSavingAll(false);
    } }
    async function transcribe(tid) { if (!tid && unsaved())
        return; setStarting(true); setError(''); try {
        setJob(await api(`/projects/${project.id}/transcribe${tid ? '?tid=' + tid : ''}`, 'POST'));
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    catch (e) {
        setError(e.message);
    }
    finally {
        setStarting(false);
    } }
    const busy = starting || job?.status === 'running';
    const trials = project?.trials ?? [];
    const saved = trials.filter(t => t.saved).length, completed = trials.filter(t => t.complete).length;
    const pending = trials.filter(t => t.asr?.pipeline_version !== 'notebook-v1' || t.asr?.profile !== t.condition).length;
    const visible = trials.filter(t => filter === 'all' || filter === 'review' && !t.complete || filter === 'complete' && t.complete || t.labels.includes(filter));
    return <><header><div><span className="eyebrow">LOCAL SPEECH ANNOTATION</span><h1>{tr("\u590D\u542C\u5DE5\u4F5C\u53F0")}</h1></div><span className="local">{tr("\u25CF \u672C\u673A\u5904\u7406 \u00B7 \u4EBA\u5DE5\u786E\u8BA4")}</span><select className="language-select" aria-label="Language / 语言" value={language} onChange={e => setLanguage(e.target.value)}><option value="zh">中文</option><option value="en">English</option></select></header><main>
 <section className="import"><div><label htmlFor="folder">{tr("\u53D7\u8BD5\u8005\u6587\u4EF6\u5939")}</label><div className="import-row"><input id="folder" value={folder} onChange={e => setFolder(e.target.value)} placeholder={tr("\u7C98\u8D34\u5305\u542B WAV / TXT \u7684\u672C\u5730\u6587\u4EF6\u5939\u5B8C\u6574\u8DEF\u5F84")}/><select aria-label={tr("\u4EFB\u52A1\u6761\u4EF6")} value={condition} onChange={e => setCondition(e.target.value)}><option value="unknown">{tr("\u81EA\u52A8\u8BC6\u522B\u6761\u4EF6")}</option><option value="number">{tr("Number \u6570\u5B57")}</option><option value="homo">Homo</option><option value="nonhomo">Non-homo</option></select><button className="primary" disabled={loading || busy || alignBusy || savingAll || uploading} onClick={load}>{loading ? tr("\u8BFB\u53D6\u4E2D\u2026") : tr("\u5BFC\u5165\u6587\u4EF6\u5939")}</button></div></div>{projects.length > 0 && <select aria-label={tr("\u6253\u5F00\u5DF2\u6709\u9879\u76EE")} value={project?.id ?? ''} disabled={busy || alignBusy || savingAll || uploading} onChange={e => open(e.target.value)}><option value="" disabled>{tr("\u6253\u5F00\u5DF2\u6709\u9879\u76EE")}</option>{projects.map(p => <option key={p.id} value={p.id}>{p.participant}</option>)}</select>}</section>
 <div className="workspace-tabs" role="tablist" aria-label={tr("\u5DE5\u4F5C\u533A")}><button role="tab" aria-selected={view === 'transcription'} className={view === 'transcription' ? 'active' : ''} onClick={() => switchView('transcription')}>{tr("\u8F6C\u5199\u4E0E\u590D\u542C")}</button><button role="tab" aria-selected={view === 'alignment'} className={view === 'alignment' ? 'active' : ''} onClick={() => switchView('alignment')}>{tr("\u5BF9\u9F50\u4E0E\u8FB9\u754C\u7F16\u8F91")}</button>{!new URLSearchParams(location.search).has('embedded') && <a href="/?v=alignment-workspace&view=alignment" target="_blank" rel="noreferrer">{tr("\u5728\u65B0\u6807\u7B7E\u6253\u5F00\u5BF9\u9F50\u5DE5\u4F5C\u533A \u2197")}</a>}</div>
 {error && <div role="alert" className="error banner">{tr(error)}</div>}
 {view === 'alignment' && <ExistingImport condition={condition} disabled={busy || alignBusy || savingAll} beforeImport={() => !unsaved()} onImported={importedExisting} onBusy={setUploading}/>}
 {saveNotice && <div className="banner" role="status">{tr(saveNotice)}{tr("\u4FDD\u5B58 TXT \u540E\uFF0C\u53EF\u70B9\u51FB\u4E0B\u65B9\u201C\u4E00\u952E\u5BF9\u9F50\u5DF2\u4FDD\u5B58\u6761\u76EE\u201D\u751F\u6210 TextGrid\u3002")}</div>}
 {starting && <div className="banner" role="status">{tr("\u6B63\u5728\u63D0\u4EA4 Whisper \u4EFB\u52A1\u2026")}</div>}
 {job && <section className={'job-panel ' + (job.errors?.length ? 'job-error' : '')} role="status"><div><b>{job.status === 'running' ? tr("\u25CC Whisper \u8FD0\u884C\u4E2D") : job.status === 'interrupted' ? tr("\u4EFB\u52A1\u5DF2\u4E2D\u65AD") : tr("Whisper \u4EFB\u52A1\u7ED3\u675F")}</b><span>{job.model ?? 'medium'} · {job.device ?? 'cpu'}{tr("\u00B7 \u5DF2\u7528\u65F6")}{job.elapsed_seconds ?? 0}{tr("\u79D2")}</span></div><p>{tr(job.message)}</p>{job.current_filename && job.status === 'running' && <p>{tr("\u5F53\u524D\u5F55\u97F3\uFF1A")}{job.current_filename}{job.audio_duration > 0 ? tr(" \u00B7 \u5DF2\u8BC6\u522B {0} / {1} \u79D2", [Math.min(job.audio_seconds ?? 0, job.audio_duration).toFixed(1), job.audio_duration.toFixed(1)]) : ''}</p>}<progress value={job.done} max={job.total || 1}/><p>{tr("\u5DF2\u5904\u7406")}{job.done} / {job.total}{tr("\u00B7 \u6210\u529F")}{job.done - (job.errors?.length ?? 0)}{tr("\u00B7 \u5931\u8D25")}{job.errors?.length ?? 0}</p>{job.errors?.length > 0 && <details open><summary>{tr("\u5931\u8D25\u8BE6\u60C5")}</summary>{job.errors.map((e, i) => <p key={i}>#{e.trial}：{tr(e.message)}</p>)}</details>}{job.status !== 'running' && pending > 0 && <button className="primary" disabled={busy} onClick={() => transcribe()}>{tr("\u4E00\u952E\u7EE7\u7EED\uFF0F\u91CD\u8BD5\u672A\u5904\u7406\u5F55\u97F3\uFF08")}{pending}{tr("）")}</button>}</section>}
 {project ? <><section className="project"><div><h2>{project.participant}</h2><p>{trials.length}{tr("\u6761\u5F55\u97F3 \u00B7 \u5DF2\u5B8C\u6210")}<b>{completed}</b> / {trials.length}{tr("\u00B7 \u5F85\u590D\u542C")}{trials.length - completed}</p><progress value={completed} max={trials.length}/></div><div className="actions"><button className="primary run-all" disabled={busy || savingAll || uploading || pending === 0} onClick={() => transcribe()}>{busy ? tr("Whisper \u8FD0\u884C\u4E2D\u2026") : pending === 0 ? tr("\u5168\u90E8\u5DF2\u8F6C\u5199") : tr("\u25B6 \u4E00\u952E\u8FD0\u884C\u5168\u90E8 Whisper\uFF08") + pending + tr('）')}</button><button className="primary" disabled={savingAll || busy || alignBusy || uploading} onClick={saveAll}>{savingAll ? tr("\u6B63\u5728\u4FDD\u5B58\u5168\u90E8 TXT\u2026") : tr("\u4E00\u952E\u4FDD\u5B58\u6240\u6709 TXT")}</button><a className="button" href={`/api/projects/${project.id}/export`} onClick={e => { if (dirty.current.size) {
            e.preventDefault();
            setError(tr("\u8BF7\u5148 Save \u4FEE\u6539\uFF0C\u518D\u5BFC\u51FA\u3002"));
        } }}>{tr("\u5BFC\u51FA\u5DF2\u4FDD\u5B58 TXT\uFF08")}{saved}{tr("）")}</a><a href={`/api/projects/${project.id}/report`}>{tr("\u5BFC\u51FA QC \u62A5\u544A")}</a><small>{tr("\u5C1A\u672A\u4FDD\u5B58")}{trials.length - saved}{tr("\u6761 \u00B7 \u6309\u539F notebook \u8FD0\u884C\uFF1B\u65E7\u7248\u7ED3\u679C\u4F1A\u91CD\u65B0\u8BC6\u522B\uFF0C\u4EBA\u5DE5\u4FDD\u5B58\u5185\u5BB9\u4FDD\u7559")}</small></div></section>
 {view === 'transcription' && <AnnotationExport key={'annotations-' + project.id} pid={project.id} disabled={busy || alignBusy || savingAll || uploading} onPrepare={() => saveAll({ annotations: true })}/>}
 <AlignmentPanel key={'alignment-' + project.id} pid={project.id} saved={saved} startRef={alignStart} onBusy={setAlignBusy} onRefresh={refreshProject} beforeStart={() => !unsaved()}/>
 {view === 'alignment' && <section className="alignment-focus"><h2>{tr("\u5728\u7EBF\u8FB9\u754C\u7F16\u8F91")}</h2><p>{tr("\u81EA\u52A8\u8BFB\u53D6\u5DF2\u4FDD\u5B58\u7684\u5BF9\u9F50\u7ED3\u679C\uFF0FTextGrid\u3002\u62D6\u52A8\u6CE2\u5F62\u4E0A\u7684\u5DE6\u53F3\u8FB9\u754C\uFF0C\u6216\u8F93\u5165\u7CBE\u786E\u65F6\u95F4\uFF1B\u70B9\u51FB\u201C\u4FDD\u5B58\u4EBA\u5DE5\u8FB9\u754C\u201D\u4FDD\u5B58 reviewed \u7248\u3002")}</p><div><button disabled={selectedTrial === '1'} onClick={() => setSelectedTrial(String(Math.max(1, Number(selectedTrial) - 1)))}>{tr("\u4E0A\u4E00\u6761")}</button><select aria-label={tr("\u9009\u62E9\u5BF9\u9F50\u5F55\u97F3")} value={selectedTrial} onChange={e => setSelectedTrial(e.target.value)}>{trials.map(t => <option key={t.id} value={t.id}>#{t.id} · {t.filename} · {t.alignments?.reviewed ? tr("\u4EBA\u5DE5\u7248") : t.alignments?.auto ? tr("\u81EA\u52A8\u7248") : tr("\u5C1A\u65E0\u5BF9\u9F50")}</option>)}</select><button disabled={Number(selectedTrial) >= trials.length} onClick={() => setSelectedTrial(String(Math.min(trials.length, Number(selectedTrial) + 1)))}>{tr("\u4E0B\u4E00\u6761")}</button></div><small>{tr("\u5C1A\u65E0\u8FB9\u754C\u65F6\uFF0C\u5148\u8FD0\u884C MFA \u5E76\u7B49\u5F85\u5B8C\u6210\uFF0C\u6216\u5728\u4E0B\u65B9\u5BFC\u5165\u5DF2\u6709 Praat TextGrid\u3002\u672A\u4FDD\u5B58\u7684\u8FB9\u754C\u5728\u672C\u9875\u5207\u6362\u5F55\u97F3\uFF0F\u5DE5\u4F5C\u533A\u65F6\u4FDD\u7559\u3002")}</small></section>}
 <nav hidden={view === 'alignment'}>{Object.entries({ all: tr("\u5168\u90E8"), review: tr("\u5F85\u590D\u542C"), complete: tr("\u5DF2\u5B8C\u6210"), ...LABELS }).map(([k, v]) => <button className={filter === k ? 'active' : ''} key={k} onClick={() => setFilter(k)}>{tr(v)}</button>)}</nav>
 <div className="trial-list">{trials.map(t => <div id={'trial-card-' + t.id} key={project.id + '/' + t.id} hidden={view === 'alignment' ? t.id !== selectedTrial : !visible.includes(t)}><TrialCard alignmentOnly={view === 'alignment'} playerVisible={view === 'alignment' ? t.id === selectedTrial : visible.includes(t)} trial={t} pid={project.id} register={registerReview} busy={busy || uploading} alignBusy={alignBusy} onAlign={(tid, reset) => alignStart.current?.(tid, reset)} onRefresh={refreshProject} onNextAlignment={nextAlignment} active={job?.status === 'running' && job.current_trial === t.id} onTranscribe={transcribe} onDirty={(id, isDirty) => isDirty ? dirty.current.add(id) : dirty.current.delete(id)} onSaved={row => setProject(p => ({ ...p, trials: p.trials.map(t => t.id === row.id ? row : t) }))}/></div>)}</div>{visible.length === 0 && <p className="empty">{tr("\u6B64\u7B5B\u9009\u4E0B\u6682\u65E0\u5F55\u97F3\u3002")}</p>}</> : <section className="empty"><h2>{tr("\u4ECE\u4E00\u4E2A\u53D7\u8BD5\u8005\u6587\u4EF6\u5939\u5F00\u59CB")}</h2><p>{tr("\u5BFC\u5165 \u2192 \u4E00\u952E\u8FD0\u884C\u5168\u90E8 Whisper \u2192 \u9010\u6761\u590D\u542C\u4FEE\u6539 \u2192 Save \u2192 \u5BFC\u51FA\u540C\u540D TXT")}</p><p>{tr("\u539F\u59CB TXT \u4FDD\u7559\u5728\u6298\u53E0\u53C2\u8003\u533A\uFF0C\u4EBA\u5DE5\u4FEE\u8BA2\u5355\u72EC\u4FDD\u5B58\u3002")}</p></section>}
 </main></>;
}
createRoot(document.getElementById('root')).render(<App />);
