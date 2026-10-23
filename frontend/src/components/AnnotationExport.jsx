import React,{useState} from 'react';
import {api} from '../api';

export default function AnnotationExport({pid,disabled,onPrepare}){
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[rows,setRows]=useState([]),[message,setMessage]=useState('');
 async function download(format){
  setBusy(true);setError('');setMessage('');
  try{
   if(!await onPrepare())return;
   const preview=await api(`/projects/${pid}/annotations?format=json`);setRows(preview.rows);
   const response=await fetch(`/api/projects/${pid}/annotations?format=${format}`);
   if(!response.ok){const data=await response.json();throw Error(data.detail||'标注导出失败')}
   const url=URL.createObjectURL(await response.blob()),a=document.createElement('a');a.href=url;a.download=format==='csv'?'annotations_sheet.csv':'annotations.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
   setMessage(`已导出 ${preview.participants} 位受试者的人工标注，每位受试者一行、标注格内多行。`);
  }catch(e){setError(e.message)}finally{setBusy(false)}
 }
 return <section className="annotation-export"><div className="alignment-title"><h3>人工标注 · Google Sheet 格式</h3><span>只汇总人工勾选的标签</span></div>
 <p>勾选自我纠正、静音、不流畅、错词／发音待核查或其他；在备注写具体问题，如“额”或“妈→马”。导出时先保存当前勾选和备注，无需逐条点 Save。</p>
 <div className="alignment-actions"><button className="primary" disabled={disabled||busy} onClick={()=>download('csv')}>{busy?'正在保存并导出…':'保存并导出 Sheet 标注'}</button><button disabled={disabled||busy} onClick={()=>download('txt')}>导出同格式标注 TXT</button></div>
 <small>CSV 两列：participant、annotation。导入 Google Sheets 后，每位受试者的 annotation 单元格包含多行记录。格式：001 - trial11 - 额 - disfluency。静音会汇总数量；勾选不会删除录音。</small>
 {message&&<p role="status">{message}</p>}{error&&<p className="error" role="alert">{error}</p>}
 {rows.length>0&&<details open><summary>导出预览（{rows.length} 位受试者）</summary>{rows.map(row=><label key={row.participant} className="annotation-preview">{row.participant}<textarea aria-label={`${row.participant} 标注预览`} readOnly rows={Math.min(12,Math.max(3,row.annotation.split('\n').length))} value={row.annotation}/></label>)}</details>}
 </section>
}
