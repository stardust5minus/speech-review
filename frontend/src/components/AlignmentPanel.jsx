import React,{useEffect,useRef,useState} from 'react';
import {api} from '../api';
export default function AlignmentPanel({pid,saved,startRef,onBusy,onRefresh,beforeStart}){
 const [status,setStatus]=useState(null),[job,setJob]=useState(null),[starting,setStarting]=useState(false),[error,setError]=useState('');
 const latest=useRef();latest.current={onRefresh,beforeStart};
 const busy=starting||job?.status==='running';
 useEffect(()=>{onBusy(busy)},[busy,onBusy]);
 useEffect(()=>{let live=true;api('/alignment/status').then(s=>{if(live)setStatus(s)}).catch(e=>{if(live)setError(e.message)});api(`/projects/${pid}/alignment-job`).then(j=>{if(live)setJob(j)}).catch(e=>{if(live)setError(e.message)});return()=>{live=false}},[pid]);
 useEffect(()=>{if(job?.status!=='running')return;const timer=setInterval(async()=>{try{const j=await api('/alignment-jobs/'+job.id);setJob(j);await latest.current.onRefresh();if(j.status!=='running')setStatus(await api('/alignment/status'))}catch(e){setError(e.message);setJob(null)}},1500);return()=>clearInterval(timer)},[job?.id,job?.status]);
 async function start(tid){if(!latest.current.beforeStart())return;setError('');setStarting(true);try{setJob(await api(`/projects/${pid}/align${tid?'?tid='+tid:''}`,'POST'))}catch(e){setError(e.message)}finally{setStarting(false)}}
 startRef.current=start;
 function exportGuard(e){if(!latest.current.beforeStart())e.preventDefault()}
 async function downloadGrids(e){e.preventDefault();if(!latest.current.beforeStart())return;setError('');try{const response=await fetch(`/api/projects/${pid}/textgrids`);if(!response.ok){const detail=await response.json();throw Error(detail.detail||'导出失败')}const url=URL.createObjectURL(await response.blob()),a=document.createElement('a');a.href=url;a.download='TextGrids.zip';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}catch(exc){setError(exc.message)}}
 return <section className="alignment-panel"><div className="alignment-title"><h3>MFA 对齐与 TextGrid</h3><span>{status?.available?'● 本地 MFA':'○ MFA 环境检查中／未就绪'}</span></div><p className="hint">{status?.message}。使用 Save 的人工修订文本；自动结果和人工边界分别保存。</p><div className="alignment-actions"><button className="primary" disabled={busy||!saved||!status?.available} onClick={()=>start()}>{busy?'MFA 对齐运行中…':'一键对齐已保存条目'}</button><a className="button" href={`/api/projects/${pid}/textgrids`} onClick={downloadGrids}>导出全部 TextGrid</a><a className="button" href={`/api/projects/${pid}/alignment.csv`} onClick={exportGuard}>alignment.csv</a><a className="button" href={`/api/projects/${pid}/export-everything`} onClick={exportGuard}>导出全部资料</a></div>
 {job&&<div className="mfa-progress" role="status"><b>{job.status==='running'?'MFA 正在运行':job.status==='interrupted'?'MFA 任务中断':'MFA 任务结束'}</b><p>{job.message} · {job.elapsed_seconds??0} 秒</p>{job.current_filename&&<p>当前：{job.current_filename}</p>}<progress value={job.done} max={job.total||1}/><p>已处理 {job.done} / {job.total} · 失败 {job.errors?.length??0}</p>{job.errors?.map((e,k)=><p className="error" key={k}>#{e.trial}：{e.message}</p>)}</div>}{error&&<p role="alert" className="error">{error}</p>}
 <small>只导出与当前文字、音频匹配的版本；自动版为 *_auto.TextGrid，人工版为 *_reviewed.TextGrid。</small></section>
}
