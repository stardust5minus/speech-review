import React,{useState,useRef,useEffect} from 'react';
import Waveform from './Waveform';
import {api} from '../api';
import AlignmentEditor from './AlignmentEditor';
export const LABELS={self_correction:'自我纠正',silent:'静音',disfluency:'不流畅',wrong_word:'错词／发音待核查',other:'其他'};
export default function TrialCard({trial:t,pid,onSaved,onTranscribe,busy,active,onDirty,alignBusy,onAlign,onRefresh,register,alignmentOnly=false,playerVisible=true}){
 const player=useRef();const [overlay,setOverlay]=useState({intervals:[],editable:false});
 const [draft,setDraft]=useState(t.corrected??''),[labels,setLabels]=useState(t.labels),[notes,setNotes]=useState(t.notes),[complete,setComplete]=useState(t.complete),[dirty,setDirty]=useState(false),[saving,setSaving]=useState(false),[message,setMessage]=useState('');
 const [version,setVersion]=useState(t.asr);
 const latestReview=useRef();latestReview.current={payload:{corrected:draft,labels,notes,complete},eligible:!!(draft.trim()||t.saved||t.asr||labels.includes('silent'))};
 useEffect(()=>{if(!register)return;register(t.id,{snapshot:()=>latestReview.current,acknowledge:payload=>{if(JSON.stringify(latestReview.current.payload)===JSON.stringify(payload)){setDirty(false);onDirty(t.id,false);setMessage('已保存')}else setMessage('已保存提交时的版本，当前修改仍需保存')}});return()=>register(t.id,null)},[register,t.id]);
 const previousCorrected=useRef(t.corrected);useEffect(()=>{if(previousCorrected.current!==t.corrected&&!dirty)setDraft(t.corrected??'');previousCorrected.current=t.corrected},[t.corrected,dirty]);
 if(version!==t.asr){setVersion(t.asr);if(!dirty)setDraft(t.corrected??'')}
 function change(fn){fn();setDirty(true);onDirty(t.id,true);setMessage('')}
 async function save(){setSaving(true);try{const row=await api(`/projects/${pid}/trials/${t.id}`,'PUT',{corrected:draft,labels,notes,complete});setDirty(false);onDirty(t.id,false);setMessage('已保存');onSaved(row)}catch(e){setMessage(e.message)}finally{setSaving(false)}}
 return <article className={'trial '+(t.complete?'completed':'')}>
 <div className="trial-header"><h2><span className="number">#{t.id.padStart(3,'0')}</span> · {t.filename}</h2><span className="badge">{t.condition==='unknown'?'条件未指定':t.condition} · {t.complete?'已完成':'待复听'}</span></div>
 <Waveform url={`/api/projects/${pid}/trials/${t.id}/audio`} {...overlay} height={alignmentOnly?170:88} visible={playerVisible} onReady={ws=>{player.current=ws}}/>
 {alignmentOnly&&<p className="alignment-transcript"><b>已保存修订文本：</b>{t.saved?t.corrected:'尚未保存，请先在“转写与复听”中保存 TXT。'}</p>}
 <div hidden={alignmentOnly}>
 <details className="model" open><summary>模型转写与诊断 <span>Whisper · {t.condition}</span></summary><p className="transcript">{t.asr?t.asr.raw||'（模型未识别到文字）':'尚未转写'}</p>
 {t.asr&&t.asr.pipeline_version!=='notebook-v1'&&<p className="error">这是旧版通用流程的结果。请按原 notebook 重新转写。</p>}
 {t.qc?.notebook_result!==undefined&&<section className="notebook-result"><b>原脚本处理结果 · 尚未采用</b><p className="transcript">{t.qc.notebook_result||'（原脚本处理后为空）'}</p>{t.qc.notebook_duplicate&&<p className="error">此结果包含原脚本的重复删除，请先核对音频。</p>}<button disabled={busy} onClick={()=>change(()=>setDraft(t.qc.notebook_result))}>采用脚本结果到复听结论</button><small>点击后仍需 Save；原始转写保留</small></section>}
 {t.asr?.parameters&&<details><summary>运行配置 · 原 notebook</summary><p>{t.asr.profile} · {t.asr.model} · {t.asr.device} · {t.asr.compute_type}</p><p className="transcript">{t.asr.parameters.initial_prompt}</p><pre style={{whiteSpace:'pre-wrap'}}>{JSON.stringify({...t.asr.parameters,initial_prompt:undefined},null,2)}</pre></details>}
 <div className="flags">{t.qc?.issues.map((i,k)=><p key={k}>⚠ {i.text}</p>)}</div><button className="subtle" disabled={busy||dirty} onClick={()=>onTranscribe(t.id)}>{active?'正在转写…':busy?'任务运行中':t.asr?'重新转写':'运行 Whisper'}</button>{dirty&&<small>先保存当前修改，再重新转写</small>}</details>
 <details className="reference"><summary>原来的 TXT · 参考备份</summary><p className="transcript">{t.original??'未找到同名 TXT'}</p></details>
 <label className="editor-label" htmlFor={'edit'+t.id}>复听结论 <small>首次预填 Whisper 文字，保留重复和填充词</small></label>
 <div className="editor"><textarea id={'edit'+t.id} rows="2" placeholder="等待 Whisper 转写，或直接输入实际听到的内容…" value={draft} onChange={e=>change(()=>setDraft(e.target.value))}/><button className="primary" disabled={saving} onClick={save}>{saving?'保存中…':'Save'}</button></div>
 <p className="hint">人工标注（可多选）：具体问题写在下方备注，顶部可一键导出 Sheet 格式。</p><div className="manual">{Object.entries(LABELS).map(([key,label])=><label key={key}><input type="checkbox" checked={labels.includes(key)} onChange={e=>change(()=>setLabels(e.target.checked?[...labels,key]:labels.filter(x=>x!==key)))}/>{label}</label>)}</div>
 <div className="bottom"><input className="notes" aria-label="备注" placeholder="标注详情／备注：例如 额、妈→马、课发成二声（用于标注导出，不写入转写 TXT）" value={notes} onChange={e=>change(()=>setNotes(e.target.value))}/><label><input type="checkbox" checked={complete} onChange={e=>change(()=>setComplete(e.target.checked))}/>标记完成</label><span role="status" className={dirty?'unsaved':'saved'}>{dirty?'有未保存修改':message|| (t.saved?'已保存':'尚未保存')}</span></div>
 </div>
 <AlignmentEditor trial={t} pid={pid} disabled={busy||dirty} alignBusy={alignBusy} onStart={onAlign} onOverlay={setOverlay} onDirty={value=>onDirty('alignment-'+t.id,value)} onChanged={onRefresh} play={(start,end)=>player.current?.play(start,end)}/>
 </article>
}
