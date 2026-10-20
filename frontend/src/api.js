export async function api(path,method='GET',body){
 const r=await fetch('/api'+path,{method,headers:{'Content-Type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)})});
 if(!r.ok){const e=await r.json().catch(()=>({detail:r.statusText}));throw Error(e.detail||'请求失败')}
 return r.json();
}
