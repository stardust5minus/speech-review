import {useLanguage} from '../i18n';
import React, { useEffect, useRef, useState } from 'react';
import { api } from '../api';
export default function AlignmentPanel({ pid, saved, startRef, onBusy, onRefresh, beforeStart }) {
    const { tr } = useLanguage();
    const [status, setStatus] = useState(null), [job, setJob] = useState(null), [starting, setStarting] = useState(false), [error, setError] = useState('');
    const latest = useRef();
    latest.current = { onRefresh, beforeStart };
    const busy = starting || job?.status === 'running';
    useEffect(() => { onBusy(busy); }, [busy, onBusy]);
    useEffect(() => { let live = true; api('/alignment/status').then(s => { if (live)
        setStatus(s); }).catch(e => { if (live)
        setError(e.message); }); api(`/projects/${pid}/alignment-job`).then(j => { if (live)
        setJob(j); }).catch(e => { if (live)
        setError(e.message); }); return () => { live = false; }; }, [pid]);
    useEffect(() => { if (job?.status !== 'running')
        return; const timer = setInterval(async () => { try {
        const j = await api('/alignment-jobs/' + job.id);
        setJob(j);
        await latest.current.onRefresh();
        if (j.status !== 'running')
            setStatus(await api('/alignment/status'));
    }
    catch (e) {
        setError(e.message);
        setJob(null);
    } }, 1500); return () => clearInterval(timer); }, [job?.id, job?.status]);
    async function start(tid, reset = false) { if (!latest.current.beforeStart())
        return; setError(''); setStarting(true); try {
        setJob(await api(`/projects/${pid}/align${tid ? '?tid=' + encodeURIComponent(tid) + (reset ? '&reset_reviewed=true' : '') : ''}`, 'POST'));
    }
    catch (e) {
        setError(e.message);
    }
    finally {
        setStarting(false);
    } }
    startRef.current = start;
    function exportGuard(e) { if (!latest.current.beforeStart())
        e.preventDefault(); }
    async function downloadGrids(e, reviewedOnly = false) { e.preventDefault(); if (!latest.current.beforeStart())
        return; setError(''); try {
        const response = await fetch(`/api/projects/${pid}/${reviewedOnly ? 'reviewed-textgrids' : 'textgrids'}`);
        if (!response.ok) {
            const detail = await response.json();
            throw Error(detail.detail || tr("\u5BFC\u51FA\u5931\u8D25"));
        }
        const url = URL.createObjectURL(await response.blob()), a = document.createElement('a');
        a.href = url;
        a.download = reviewedOnly ? 'reviewed_TextGrids.zip' : 'TextGrids.zip';
        a.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
    catch (exc) {
        setError(exc.message);
    } }
    return <section className="alignment-panel"><div className="alignment-title"><h3>{tr("MFA \u5BF9\u9F50\u4E0E TextGrid")}</h3><span>{status?.available ? tr("\u25CF \u672C\u5730 MFA") : tr("\u25CB MFA \u73AF\u5883\u68C0\u67E5\u4E2D\uFF0F\u672A\u5C31\u7EEA")}</span></div><p className="hint">{tr(status?.message)}{tr("\u3002\u4F7F\u7528 Save \u7684\u4EBA\u5DE5\u4FEE\u8BA2\u6587\u672C\uFF1B\u81EA\u52A8\u7ED3\u679C\u548C\u4EBA\u5DE5\u8FB9\u754C\u5206\u522B\u4FDD\u5B58\u3002")}</p><div className="alignment-actions"><button className="primary" disabled={busy || !saved || !status?.available} onClick={() => start()}>{busy ? tr("MFA \u5BF9\u9F50\u8FD0\u884C\u4E2D\u2026") : tr("\u4E00\u952E\u5BF9\u9F50\u5DF2\u4FDD\u5B58\u6761\u76EE")}</button><a className="button" href={`/api/projects/${pid}/textgrids`} onClick={e => downloadGrids(e)}>{tr("\u5BFC\u51FA\u5168\u90E8 TextGrid")}</a><a className="button" href={`/api/projects/${pid}/reviewed-textgrids`} onClick={e => downloadGrids(e, true)}>{tr("\u4E00\u952E\u5BFC\u51FA\u4EBA\u5DE5 TextGrid")}</a><a className="button" href={`/api/projects/${pid}/alignment.csv`} onClick={exportGuard}>alignment.csv</a><a className="button" href={`/api/projects/${pid}/export-everything`} onClick={exportGuard}>{tr("\u5BFC\u51FA\u5168\u90E8\u8D44\u6599")}</a></div>
 {job && <div className="mfa-progress" role="status"><b>{job.status === 'running' ? tr("MFA \u6B63\u5728\u8FD0\u884C") : job.status === 'interrupted' ? tr("MFA \u4EFB\u52A1\u4E2D\u65AD") : tr("MFA \u4EFB\u52A1\u7ED3\u675F")}</b><p>{tr(job.message)} · {job.elapsed_seconds ?? 0}{tr("\u79D2")}</p>{job.current_filename && <p>{tr("\u5F53\u524D\uFF1A")}{job.current_filename}</p>}<progress value={job.done} max={job.total || 1}/><p>{tr("\u5DF2\u5904\u7406")}{job.done} / {job.total}{tr("\u00B7 \u5931\u8D25")}{job.errors?.length ?? 0}</p>{job.errors?.map((e, k) => <p className="error" key={k}>#{e.trial}：{tr(e.message)}</p>)}</div>}{error && <p role="alert" className="error">{tr(error)}</p>}
 <details className="usage-help"><summary>{tr("版本与导出说明")}</summary> <small>{tr("\u53EA\u5BFC\u51FA\u4E0E\u5F53\u524D\u6587\u5B57\u3001\u97F3\u9891\u5339\u914D\u7684\u7248\u672C\uFF1B\u81EA\u52A8\u7248\u4E3A *_auto.TextGrid\uFF0C\u4EBA\u5DE5\u7248\u4E3A *_reviewed.TextGrid\u3002\u300C\u4E00\u952E\u5BFC\u51FA\u4EBA\u5DE5\u300D\u53EA\u542B\u4EBA\u5DE5\u7248\uFF0C\u6309\u97F3\u9891\u4E3B\u540D\u547D\u540D\uFF08\u4F8B\u5982 3nonhomo_069_trial9.TextGrid\uFF09\u3002")}</small></details></section>;
}
