import React,{useRef,useState} from 'react';

export default function ExistingImport({condition,disabled,beforeImport,onImported,onBusy}){
 const filesInput=useRef(),folderInput=useRef();
 const [title,setTitle]=useState(''),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState(''),[warnings,setWarnings]=useState([]);
 async function upload(files){
  if(!files.length||disabled||busy||!beforeImport())return;
  setBusy(true);onBusy(true);setError('');setMessage('正在上传、配对并校验已有标注…');setWarnings([]);
  try{
   const form=new FormData();form.append('condition',condition);form.append('title',title);
   for(const file of files)form.append('files',file,file.webkitRelativePath||file.name);
   const response=await fetch('/api/import-existing',{method:'POST',body:form});
   const data=await response.json().catch(()=>({detail:`上传失败（HTTP ${response.status}），文件较大时请分批导入。`}));if(!response.ok)throw Error(data.detail||'导入失败');
   await onImported(data.project);setWarnings(data.warnings??[]);setMessage(`已导入 ${data.imported} 条已有标注，可直接播放并编辑人工边界。`);
  }catch(e){setMessage('');setError(e.message)}finally{setBusy(false);onBusy(false)}
 }
 return <section className="existing-import"><h2>一键导入已有 WAV + TXT + TextGrid</h2>
 <p>按同一文件主名自动配对，支持多条录音。无需重新转写或运行 MFA，TextGrid 作为人工版载入，原 TXT 保留作参考。</p>
 <div className="alignment-actions"><input aria-label="已有标注项目名称" placeholder="项目名称（可选）" value={title} disabled={disabled||busy} onChange={e=>setTitle(e.target.value)}/>
 <button className="primary" disabled={disabled||busy} onClick={()=>{if(beforeImport())filesInput.current.click()}}>{busy?'正在导入…':'选择文件并一键导入'}</button>
 <button disabled={disabled||busy} onClick={()=>{if(beforeImport())folderInput.current.click()}}>选择整个文件夹导入</button></div>
 <input ref={filesInput} aria-label="导入已有标注文件" type="file" accept=".wav,.WAV,.txt,.TXT,.TextGrid,.textgrid" multiple hidden disabled={disabled||busy} onChange={e=>{upload(Array.from(e.target.files));e.target.value=''}}/>
 <input ref={folderInput} aria-label="导入已有标注文件夹" type="file" webkitdirectory="" multiple hidden disabled={disabled||busy} onChange={e=>{upload(Array.from(e.target.files));e.target.value=''}}/>
 <small>例如：3nonhomo_069_trial9.wav / .txt / .TextGrid。也识别 _reviewed.TextGrid、_auto.TextGrid；同名无后缀版优先，其次人工版，再其次自动版。创建独立新项目，文件复制到工作台保存目录。</small>
 {message&&<p role="status">{message}</p>}{error&&<p className="error" role="alert">{error}</p>}{warnings.length>0&&<details open><summary>导入提示（{warnings.length}）</summary>{warnings.map((warning,k)=><p key={k}>{warning}</p>)}</details>}
 </section>
}
