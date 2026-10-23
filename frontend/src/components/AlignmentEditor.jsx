import {useLanguage} from '../i18n';
import React, { useEffect, useRef, useState } from 'react';
import { api } from '../api';
import { fullTier, splitInterval, removeLeftBoundary } from '../alignmentEditing';
export default function AlignmentEditor({ trial: t, pid, disabled, alignBusy, onStart, onOverlay, onDirty, onChanged, onNext, play }) {
    const { tr } = useLanguage();
    const [records, setRecords] = useState({ auto: null, reviewed: null }), [version, setVersion] = useState('auto'), [base, setBase] = useState(null), [draft, setDraft] = useState([]), [undo, setUndo] = useState([]), [message, setMessage] = useState(''), [saving, setSaving] = useState(false);
    const [selected, setSelected] = useState(0), [cursor, setCursor] = useState(0);
    const saveLock = useRef(false);
    const labelInput = useRef(), labelCaret = useRef(null), commands = useRef();
    const dirty = !!base && JSON.stringify(draft) !== JSON.stringify(fullTier(base.intervals, base.duration)), dirtyRef = useRef(false);
    dirtyRef.current = dirty;
    const stale = !!base && (base.stale || base.transcript !== t.corrected), canEdit = !!base && !stale && !disabled && !alignBusy && !saving;
    const current = useRef();
    current.current = { draft, canEdit };
    const changeRef = useRef();
    changeRef.current = next => { if (!current.current.canEdit)
        return; setUndo(history => [...history, current.current.draft]); setDraft(next); setMessage(''); };
    useEffect(() => { let active = true; api(`/projects/${pid}/trials/${t.id}/alignment`).then(data => { if (!active)
        return; setRecords(data); if (!dirtyRef.current) {
        const v = data.reviewed ? 'reviewed' : 'auto';
        setVersion(v);
        setBase(data[v]);
        setDraft(data[v] ? fullTier(data[v].intervals, data[v].duration) : []);
        setSelected(0);
        setCursor(0);
        setUndo([]);
    } }).catch(e => { if (active)
        setMessage(e.message); }); return () => { active = false; }; }, [pid, t.id, t.corrected, t.alignments?.auto?.id, t.alignments?.reviewed?.id]);
    useEffect(() => { onDirty(dirty); }, [dirty]);
    useEffect(() => { onOverlay({ intervals: draft, editable: canEdit, onIntervalsChange: next => changeRef.current(next), selectedIndex: selected, editCursor: cursor, onPlaybackPause: time => commands.current.pauseAt(time), onCursorChange: time => commands.current.selectTime(time), onSelectInterval: (index, time) => commands.current.select(index, time), onKeyDown: event => commands.current.keyDown(event) }); }, [draft, canEdit, onOverlay, selected, cursor]);
    function choose(v) { setVersion(v); setBase(records[v]); setDraft(records[v] ? fullTier(records[v].intervals, records[v].duration) : []); setSelected(0); setCursor(0); setUndo([]); setMessage(''); }
    function editBoundary(index, field, value) { const changed = draft.map(i => ({ ...i })), old = draft[index]; changed[index][field] = value; if (field === 'start' && index > 0 && Math.abs(draft[index - 1].end - old.start) < 1e-6)
        changed[index - 1].end = value; if (field === 'end' && index + 1 < draft.length && Math.abs(draft[index + 1].start - old.end) < 1e-6)
        changed[index + 1].start = value; changeRef.current(changed); }
    async function save(advance = false) { if (saveLock.current || !canEdit) return; saveLock.current = true; setSaving(true); setMessage(''); try {
        if (draft.some((i, k) => !Number.isFinite(i.start) || !Number.isFinite(i.end) || i.start < 0 || i.end > base.duration || i.end <= i.start || (k && i.start < draft[k - 1].end)))
            throw Error(tr("\u8FB9\u754C\u5FC5\u987B\u5728\u97F3\u9891\u8303\u56F4\u5185\uFF0C\u5F00\u59CB\u5C0F\u4E8E\u7ED3\u675F\uFF0C\u4E14\u4E0D\u80FD\u91CD\u53E0"));
        const data = await api(`/projects/${pid}/trials/${t.id}/alignment`, 'PUT', { intervals: draft, transcript: base.transcript, base_id: base.id, update_transcript: true });
        setRecords(data);
        setVersion('reviewed');
        setBase(data.reviewed);
        setDraft(fullTier(data.reviewed.intervals, data.reviewed.duration));
        setUndo([]);
        setMessage(tr("\u4EBA\u5DE5\u8FB9\u754C\u4E0E\u6587\u5B57\u5DF2\u4FDD\u5B58\uFF0CTXT \u5DF2\u540C\u6B65"));
        await onChanged?.();
        if (advance === true && onNext && await onNext() === false) setMessage(tr("已保存，这是最后一条录音。"));
    }
    catch (e) {
        setMessage(e.message);
    }
    finally {
        saveLock.current = false;
        setSaving(false);
    } }
    async function importFile(file) { if (!file)
        return; setSaving(true); try {
        const bytes = new Uint8Array(await file.arrayBuffer());
        let encoding = 'utf-8';
        if (bytes[0] === 255 && bytes[1] === 254)
            encoding = 'utf-16le';
        else if (bytes[0] === 254 && bytes[1] === 255)
            encoding = 'utf-16be';
        const content = new TextDecoder(encoding).decode(bytes);
        const data = await api(`/projects/${pid}/trials/${t.id}/alignment/import`, 'POST', { content });
        setRecords(data);
        setVersion('reviewed');
        setBase(data.reviewed);
        setDraft(fullTier(data.reviewed.intervals, data.reviewed.duration));
        setUndo([]);
        setMessage(tr("\u5DF2\u5BFC\u5165 Praat \u4EBA\u5DE5\u5BA1\u9605\u7248\u672C"));
        onChanged?.();
    }
    catch (e) {
        setMessage(e.message);
    }
    finally {
        setSaving(false);
    } }
    function select(index, time = draft[index]?.start ?? 0) { if (index !== selected)
        labelCaret.current = null; setSelected(index); setCursor(time); }
    function selectTime(time) { if (!Number.isFinite(time)) return; const at = Math.max(0, Math.min(base?.duration ?? time, time)); const index = draft.findIndex(i => at >= i.start && at < i.end); if (index >= 0) select(index, at); else setCursor(at); }
    function pauseAt(time) { setCursor(time); const index = draft.findIndex(i => time > i.start + .0001 && time < i.end - .0001); if (index >= 0) select(index, time); }
    function applyOperation(operation) { try {
        const result = operation();
        changeRef.current(result.intervals);
        setSelected(result.index);
        setMessage('');
    }
    catch (e) {
        setMessage(e.message);
    } }
    function insert() { if (!canEdit)
        return; const caret = document.activeElement === labelInput.current ? labelInput.current.selectionStart : labelCaret.current; applyOperation(() => splitInterval(draft, cursor, caret)); }
    function remove() { if (!canEdit)
        return; applyOperation(() => removeLeftBoundary(draft, selected)); }
    function undoEdit() { if (!canEdit || !undo.length)
        return; setDraft(undo.at(-1)); setUndo(undo.slice(0, -1)); setSelected(0); }
    function keyDown(e) {
        if (e.nativeEvent?.isComposing || e.isComposing || !canEdit || saving)
            return;
        const typing = e.target.matches('input,textarea,[contenteditable="true"]');
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && onNext) { e.preventDefault(); if (!e.repeat) save(true); return; }
        if (['Delete', 'Backspace'].includes(e.key) && !typing && !e.ctrlKey && !e.metaKey && !e.altKey) {
            e.preventDefault();
            remove();
            return;
        }
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
            e.preventDefault();
            save();
            return;
        }
        if (e.altKey && e.key === 'Backspace') {
            e.preventDefault();
            remove();
            return;
        }
        if (e.key === 'Enter' && !e.ctrlKey && !e.metaKey && !e.altKey && (!typing || e.target === labelInput.current)) {
            e.preventDefault();
            insert();
            return;
        }
        if (typing)
            return;
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
            e.preventDefault();
            undoEdit();
        }
        else if (e.key === ' ') {
            e.preventDefault();
            if (draft[selected])
                play(draft[selected].start, draft[selected].end);
        }
        else if (e.altKey && ['ArrowLeft', 'ArrowRight'].includes(e.key)) {
            e.preventDefault();
            select(Math.max(0, Math.min(draft.length - 1, selected + (e.key === 'ArrowLeft' ? -1 : 1))));
        }
        else if (!e.ctrlKey && !e.metaKey && !e.altKey && e.key.length === 1) {
            e.preventDefault();
            labelInput.current?.focus();
            changeRef.current(draft.map((i, k) => k === selected ? { ...i, text: i.text + e.key } : i));
        }
    }
    commands.current = { select, selectTime, pauseAt, keyDown };
    return <section className="alignment-editor" tabIndex={0} onKeyDown={keyDown}><div className="alignment-title"><h3>{tr("\u5F3A\u5236\u5BF9\u9F50 \u00B7 TextGrid")}</h3><span>{tr("MFA \u00B7 \u4EBA\u5DE5\u4FEE\u8BA2\u6587\u672C")}</span></div>
 <div className="alignment-actions"><button disabled={!t.saved || !t.corrected?.trim() || disabled || alignBusy || dirty} onClick={() => onStart(t.id)}>{alignBusy ? tr("MFA \u5BF9\u9F50\u4EFB\u52A1\u8FD0\u884C\u4E2D\u2026") : records.auto ? tr("\u91CD\u65B0\u5F3A\u5236\u5BF9\u9F50") : tr("\u5F3A\u5236\u5BF9\u9F50\u5DF2\u4FDD\u5B58\u6587\u672C")}</button><label className={'button ' + (!t.saved || disabled || dirty ? 'inactive' : '')}>{tr("\u5BFC\u5165 Praat TextGrid")}<input type="file" accept=".TextGrid,.textgrid" hidden disabled={!t.saved || disabled || dirty || saving} onChange={e => { importFile(e.target.files[0]); e.target.value = ''; }}/></label>{base && !stale && !dirty && <a className="button" href={`/api/projects/${pid}/trials/${t.id}/textgrid?version=${version}`}>{tr("\u4E0B\u8F7D")}{version === 'reviewed' ? tr("\u4EBA\u5DE5\u7248") : tr("\u81EA\u52A8\u7248")} TextGrid</a>}</div>
 {!t.saved && <p className="hint">{tr("\u5148\u590D\u542C\u5E76 Save \u4FEE\u8BA2\u6587\u5B57\uFF0C\u518D\u8FD0\u884C\u5BF9\u9F50\u3002\u5BF9\u9F50\u4E0D\u4F1A\u4F7F\u7528\u539F\u59CB Whisper \u6587\u672C\u4EE3\u66FF\u4EBA\u5DE5\u6587\u672C\u3002")}</p>}
 {base ? <><div className="alignment-meta"><select aria-label={tr("\u5BF9\u9F50\u7248\u672C")} value={version} disabled={dirty} onChange={e => choose(e.target.value)}><option value="auto" disabled={!records.auto}>{tr("\u81EA\u52A8\u5BF9\u9F50")}</option><option value="reviewed" disabled={!records.reviewed}>{tr("\u4EBA\u5DE5\u5BA1\u9605")}</option></select><span>{draft.length}{tr("\u4E2A\u533A\u95F4 \u00B7")}{base.duration.toFixed(3)}{tr("\u79D2")}{dirty ? tr(" \u00B7 \u8FB9\u754C\u5C1A\u672A\u4FDD\u5B58") : ''}</span></div>
 {stale ? <p className="error">{tr("\u6B64\u5BF9\u9F50\u5DF2\u8FC7\u671F\uFF1A\u6587\u5B57\u6216\u97F3\u9891\u5DF2\u6539\u53D8\u3002\u8BF7\u4FDD\u5B58\u5F53\u524D\u6587\u5B57\u5E76\u91CD\u65B0\u5BF9\u9F50\u3002\u539F\u4EBA\u5DE5\u7248\u672C\u4ECD\u4FDD\u7559\u3002")}</p> : <p className="hint">{tr("\u5355\u51FB\u4E0B\u65B9\u533A\u95F4\u6761\u590D\u542C\u5E76\u9009\u4E2D\uFF1B\u5728\u4E0A\u65B9\u6CE2\u5F62\u62D6\u52A8\u8FB9\u754C\u6216\u8F93\u5165\u7CBE\u786E\u65F6\u95F4\uFF0C\u76F8\u90BB\u5171\u7528\u8FB9\u754C\u4F1A\u8054\u52A8\u3002\u9009\u4E2D\u533A\u95F4\u540E\u53EF\u76F4\u63A5\u4FEE\u6539\u6587\u5B57\uFF1B\u4FDD\u5B58\u65F6\u540C\u6B65\u4FEE\u8BA2 TXT\u3002Enter \u589E\u52A0\u8FB9\u754C\uFF0CDelete / Backspace \u5220\u9664\u6240\u9009\u533A\u95F4\u5DE6\u8FB9\u754C\uFF0CCtrl/Cmd + Z \u64A4\u9500\uFF0CCtrl/Cmd + S \u4FDD\u5B58\u3002")}</p>}
 <div className="textgrid-tools"><label>{tr("\u5149\u6807\uFF08\u79D2\uFF09")}<input aria-label={tr("\u7F16\u8F91\u5149\u6807\uFF08\u79D2\uFF09")} type="number" step="0.001" min="0" max={base.duration} value={cursor} disabled={!canEdit} onChange={e => selectTime(Number(e.target.value))}/></label><button disabled={!canEdit} onClick={insert}>{tr("\u589E\u52A0\u8FB9\u754C\uFF08Enter\uFF09")}</button><button disabled={!canEdit || selected === 0} onClick={remove}>{tr("\u5220\u9664\u5DE6\u8FB9\u754C\uFF08Delete / Backspace\uFF09")}</button><button disabled={!canEdit || !draft[selected]?.text} onClick={() => changeRef.current(draft.map((i, k) => k === selected ? { ...i, text: '' } : i))}>{tr("\u6E05\u7A7A\u9009\u4E2D\u6587\u5B57")}</button></div>
 <label className="textgrid-label">{tr("\u9009\u4E2D\u533A\u95F4")}{selected + 1}{tr("\u7684\u6587\u5B57\uFF08\u53EF\u589E\u52A0\u3001\u5220\u9664\u6216\u7559\u7A7A\uFF09")}<input ref={labelInput} aria-label={tr("\u9009\u4E2D\u533A\u95F4\u6587\u5B57")} disabled={!canEdit || !draft[selected]} value={draft[selected]?.text ?? ''} onSelect={e => { labelCaret.current = e.target.selectionStart; }} onChange={e => { labelCaret.current = e.target.selectionStart; changeRef.current(draft.map((i, k) => k === selected ? { ...i, text: e.target.value } : i)); }}/></label>
 <p className="hint">{tr("\u5220\u9664\u8FB9\u754C\u4F1A\u5408\u5E76\u4E24\u4FA7\u6587\u5B57\uFF1BEnter \u6309\u6587\u5B57\u8F93\u5165\u6846\u4E2D\u7684\u5149\u6807\u4F4D\u7F6E\u62C6\u5206\u6587\u5B57\u3002\u5728\u6CE2\u5F62\u70B9\u51FB\u8BBE\u7F6E\u65F6\u95F4\u5149\u6807\uFF0C\u518D\u6309 Enter\u3002\u9996\u5C3E\u97F3\u9891\u8FB9\u754C\u56FA\u5B9A\u3002")}</p>
 <div className="word-strip" aria-label={tr("\u5B57\u8BCD\u533A\u95F4")}>{draft.map((i, k) => <button key={k} title={tr("\u5355\u51FB\u590D\u542C {0}\u2013{1} \u79D2", [i.start.toFixed(3), i.end.toFixed(3)])} style={{ left: `${i.start / base.duration * 100}%`, width: `${(i.end - i.start) / base.duration * 100}%` }} className={selected === k ? 'selected' : ''} onClick={() => { select(k, i.start); play(i.start, i.end); }}>{i.text || tr("\uFF08\u7A7A\uFF09")}</button>)}</div>
 <div className="boundary-scroll"><table className="boundaries"><thead><tr><th>{tr("\u5B57\u8BCD")}</th><th>{tr("\u5F00\u59CB\uFF08\u79D2\uFF09")}</th><th>{tr("\u7ED3\u675F\uFF08\u79D2\uFF09")}</th><th>{tr("\u590D\u542C")}</th></tr></thead><tbody>{draft.map((i, k) => <tr key={k} className={selected === k ? 'selected' : ''}><td><button aria-label={tr("\u9009\u62E9\u533A\u95F4 {0}", [k + 1])} onClick={() => select(k, i.start)}>{i.text || tr("\uFF08\u7A7A\uFF09")}</button></td>{['start', 'end'].map(field => <td key={field}><input aria-label={`${k + 1} ${field}`} type="number" step="0.001" min="0" max={base.duration} value={i[field]} disabled={!canEdit || (k === 0 && field === 'start') || (k === draft.length - 1 && field === 'end')} onChange={e => editBoundary(k, field, Number(e.target.value))}/></td>)}<td><button onClick={() => play(i.start, i.end)}>▶</button></td></tr>)}</tbody></table></div>
 <div className="alignment-actions"><button className="primary" disabled={!canEdit || saving} onClick={save}>{saving ? tr("\u4FDD\u5B58\u4E2D\u2026") : tr("\u4FDD\u5B58\u4EBA\u5DE5\u8FB9\u754C")}</button>{onNext && <button className="primary save-next" disabled={!canEdit || saving} onClick={() => save(true)} title={tr("保存并下一条（Ctrl / Cmd + Enter）")}>{saving ? tr("保存中…") : tr("保存并下一条")}</button>}<button disabled={!undo.length || !canEdit} onClick={undoEdit}>{tr("\u64A4\u9500\u4FEE\u6539")}</button><button disabled={!dirty} onClick={() => { setDraft(fullTier(base.intervals, base.duration)); setUndo([]); setMessage(''); }}>{tr("\u653E\u5F03\u672A\u4FDD\u5B58\u8FB9\u754C")}</button><small>{tr("\u81EA\u52A8\u4E0E\u4EBA\u5DE5\u7248\u672C\u72EC\u7ACB\u4FDD\u5B58\uFF0C\u91CD\u65B0\u5BF9\u9F50\u4E0D\u4F1A\u8986\u76D6\u4EBA\u5DE5\u7248\u3002")}</small></div></> : <p className="hint">{tr("\u5C1A\u65E0\u5BF9\u9F50\u7ED3\u679C\u3002\u751F\u6210\u540E\u53EF\u76F4\u63A5\u5728\u6CE2\u5F62\u4E0A\u8C03\u6574\u8FB9\u754C\uFF0C\u4E5F\u53EF\u5BFC\u5165 Praat \u7684 words \u5C42\u3002")}</p>}
 {message && <p role="status" className="alignment-message">{tr(message)}</p>}
 </section>;
}
