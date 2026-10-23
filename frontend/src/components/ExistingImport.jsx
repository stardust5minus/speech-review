import {useLanguage} from '../i18n';
import React, { useRef, useState } from 'react';
export default function ExistingImport({ condition, disabled, beforeImport, onImported, onBusy }) {
    const { tr } = useLanguage();
    const filesInput = useRef(), folderInput = useRef();
    const [title, setTitle] = useState(''), [busy, setBusy] = useState(false), [message, setMessage] = useState(''), [error, setError] = useState(''), [warnings, setWarnings] = useState([]);
    async function upload(files) {
        if (!files.length || disabled || busy || !beforeImport())
            return;
        setBusy(true);
        onBusy(true);
        setError('');
        setMessage(tr("\u6B63\u5728\u4E0A\u4F20\u3001\u914D\u5BF9\u5E76\u6821\u9A8C\u5DF2\u6709\u6807\u6CE8\u2026"));
        setWarnings([]);
        try {
            const form = new FormData();
            form.append('condition', condition);
            form.append('title', title);
            for (const file of files)
                form.append('files', file, file.webkitRelativePath || file.name);
            const response = await fetch('/api/import-existing', { method: 'POST', body: form });
            const data = await response.json().catch(() => ({ detail: tr("\u4E0A\u4F20\u5931\u8D25\uFF08HTTP {0}\uFF09\uFF0C\u6587\u4EF6\u8F83\u5927\u65F6\u8BF7\u5206\u6279\u5BFC\u5165\u3002", [response.status]) }));
            if (!response.ok)
                throw Error(data.detail || tr("\u5BFC\u5165\u5931\u8D25"));
            await onImported(data.project);
            setWarnings(data.warnings ?? []);
            setMessage(tr("\u5DF2\u5BFC\u5165 {0} \u6761\u5DF2\u6709\u6807\u6CE8\uFF0C\u53EF\u76F4\u63A5\u64AD\u653E\u5E76\u7F16\u8F91\u4EBA\u5DE5\u8FB9\u754C\u3002", [data.imported]));
        }
        catch (e) {
            setMessage('');
            setError(e.message);
        }
        finally {
            setBusy(false);
            onBusy(false);
        }
    }
    return <section className="existing-import"><h2>{tr("\u4E00\u952E\u5BFC\u5165\u5DF2\u6709 WAV + TXT + TextGrid")}</h2>
 <p>{tr("\u6309\u540C\u4E00\u6587\u4EF6\u4E3B\u540D\u81EA\u52A8\u914D\u5BF9\uFF0C\u652F\u6301\u591A\u6761\u5F55\u97F3\u3002\u65E0\u9700\u91CD\u65B0\u8F6C\u5199\u6216\u8FD0\u884C MFA\uFF0CTextGrid \u4F5C\u4E3A\u4EBA\u5DE5\u7248\u8F7D\u5165\uFF0C\u539F TXT \u4FDD\u7559\u4F5C\u53C2\u8003\u3002")}</p>
 <div className="alignment-actions"><input aria-label={tr("\u5DF2\u6709\u6807\u6CE8\u9879\u76EE\u540D\u79F0")} placeholder={tr("\u9879\u76EE\u540D\u79F0\uFF08\u53EF\u9009\uFF09")} value={title} disabled={disabled || busy} onChange={e => setTitle(e.target.value)}/>
 <button className="primary" disabled={disabled || busy} onClick={() => { if (beforeImport())
        filesInput.current.click(); }}>{busy ? tr("\u6B63\u5728\u5BFC\u5165\u2026") : tr("\u9009\u62E9\u6587\u4EF6\u5E76\u4E00\u952E\u5BFC\u5165")}</button>
 <button disabled={disabled || busy} onClick={() => { if (beforeImport())
        folderInput.current.click(); }}>{tr("\u9009\u62E9\u6574\u4E2A\u6587\u4EF6\u5939\u5BFC\u5165")}</button></div>
 <input ref={filesInput} aria-label={tr("\u5BFC\u5165\u5DF2\u6709\u6807\u6CE8\u6587\u4EF6")} type="file" accept=".wav,.WAV,.txt,.TXT,.TextGrid,.textgrid" multiple hidden disabled={disabled || busy} onChange={e => { upload(Array.from(e.target.files)); e.target.value = ''; }}/>
 <input ref={folderInput} aria-label={tr("\u5BFC\u5165\u5DF2\u6709\u6807\u6CE8\u6587\u4EF6\u5939")} type="file" webkitdirectory="" multiple hidden disabled={disabled || busy} onChange={e => { upload(Array.from(e.target.files)); e.target.value = ''; }}/>
 <small>{tr("\u4F8B\u5982\uFF1A3nonhomo_069_trial9.wav / .txt / .TextGrid\u3002\u4E5F\u8BC6\u522B _reviewed.TextGrid\u3001_auto.TextGrid\uFF1B\u540C\u540D\u65E0\u540E\u7F00\u7248\u4F18\u5148\uFF0C\u5176\u6B21\u4EBA\u5DE5\u7248\uFF0C\u518D\u5176\u6B21\u81EA\u52A8\u7248\u3002\u521B\u5EFA\u72EC\u7ACB\u65B0\u9879\u76EE\uFF0C\u6587\u4EF6\u590D\u5236\u5230\u5DE5\u4F5C\u53F0\u4FDD\u5B58\u76EE\u5F55\u3002")}</small>
 {message && <p role="status">{tr(message)}</p>}{error && <p className="error" role="alert">{tr(error)}</p>}{warnings.length > 0 && <details open><summary>{tr("\u5BFC\u5165\u63D0\u793A\uFF08")}{warnings.length}{tr("）")}</summary>{warnings.map((warning, k) => <p key={k}>{tr(warning)}</p>)}</details>}
 </section>;
}
