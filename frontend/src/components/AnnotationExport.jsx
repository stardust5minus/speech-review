import {useLanguage} from '../i18n';
import React, { useState } from 'react';
import { api } from '../api';
export default function AnnotationExport({ pid, disabled, onPrepare }) {
    const { tr } = useLanguage();
    const [busy, setBusy] = useState(false), [error, setError] = useState(''), [rows, setRows] = useState([]), [message, setMessage] = useState('');
    async function download(format) {
        setBusy(true);
        setError('');
        setMessage('');
        try {
            if (!await onPrepare())
                return;
            const preview = await api(`/projects/${pid}/annotations?format=json`);
            setRows(preview.rows);
            const response = await fetch(`/api/projects/${pid}/annotations?format=${format}`);
            if (!response.ok) {
                const data = await response.json();
                throw Error(data.detail || tr("\u6807\u6CE8\u5BFC\u51FA\u5931\u8D25"));
            }
            const url = URL.createObjectURL(await response.blob()), a = document.createElement('a');
            a.href = url;
            a.download = format === 'csv' ? 'annotations_sheet.csv' : 'annotations.txt';
            a.click();
            setTimeout(() => URL.revokeObjectURL(url), 1000);
            setMessage(tr("\u5DF2\u5BFC\u51FA {0} \u4F4D\u53D7\u8BD5\u8005\u7684\u4EBA\u5DE5\u6807\u6CE8\uFF0C\u6BCF\u4F4D\u53D7\u8BD5\u8005\u4E00\u884C\u3001\u6807\u6CE8\u683C\u5185\u591A\u884C\u3002", [preview.participants]));
        }
        catch (e) {
            setError(e.message);
        }
        finally {
            setBusy(false);
        }
    }
    return <section className="annotation-export"><div className="alignment-title"><h3>{tr("\u4EBA\u5DE5\u6807\u6CE8 \u00B7 Google Sheet \u683C\u5F0F")}</h3><span>{tr("\u53EA\u6C47\u603B\u4EBA\u5DE5\u52FE\u9009\u7684\u6807\u7B7E")}</span></div>
 <p>{tr("\u52FE\u9009\u81EA\u6211\u7EA0\u6B63\u3001\u9759\u97F3\u3001\u4E0D\u6D41\u7545\u3001\u9519\u8BCD\uFF0F\u53D1\u97F3\u5F85\u6838\u67E5\u6216\u5176\u4ED6\uFF1B\u5728\u5907\u6CE8\u5199\u5177\u4F53\u95EE\u9898\uFF0C\u5982\u201C\u989D\u201D\u6216\u201C\u5988\u2192\u9A6C\u201D\u3002\u5BFC\u51FA\u65F6\u5148\u4FDD\u5B58\u5F53\u524D\u52FE\u9009\u548C\u5907\u6CE8\uFF0C\u65E0\u9700\u9010\u6761\u70B9 Save\u3002")}</p>
 <div className="alignment-actions"><button className="primary" disabled={disabled || busy} onClick={() => download('csv')}>{busy ? tr("\u6B63\u5728\u4FDD\u5B58\u5E76\u5BFC\u51FA\u2026") : tr("\u4FDD\u5B58\u5E76\u5BFC\u51FA Sheet \u6807\u6CE8")}</button><button disabled={disabled || busy} onClick={() => download('txt')}>{tr("\u5BFC\u51FA\u540C\u683C\u5F0F\u6807\u6CE8 TXT")}</button></div>
 <small>{tr("CSV \u4E24\u5217\uFF1Aparticipant\u3001annotation\u3002\u5BFC\u5165 Google Sheets \u540E\uFF0C\u6BCF\u4F4D\u53D7\u8BD5\u8005\u7684 annotation \u5355\u5143\u683C\u5305\u542B\u591A\u884C\u8BB0\u5F55\u3002\u683C\u5F0F\uFF1A001 - trial11 - \u989D - disfluency\u3002\u9759\u97F3\u4F1A\u6C47\u603B\u6570\u91CF\uFF1B\u52FE\u9009\u4E0D\u4F1A\u5220\u9664\u5F55\u97F3\u3002")}</small>
 {message && <p role="status">{tr(message)}</p>}{error && <p className="error" role="alert">{tr(error)}</p>}
 {rows.length > 0 && <details open><summary>{tr("\u5BFC\u51FA\u9884\u89C8\uFF08")}{rows.length}{tr("\u4F4D\u53D7\u8BD5\u8005\uFF09")}</summary>{rows.map(row => <label key={row.participant} className="annotation-preview">{row.participant}<textarea aria-label={tr("{0} \u6807\u6CE8\u9884\u89C8", [row.participant])} readOnly rows={Math.min(12, Math.max(3, row.annotation.split('\n').length))} value={row.annotation}/></label>)}</details>}
 </section>;
}
