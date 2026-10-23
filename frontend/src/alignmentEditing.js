export function fullTier(intervals,duration){
 const result=[];let cursor=0;
 for(const i of intervals){if(i.start>cursor+1e-7)result.push({start:cursor,end:i.start,text:''});result.push({...i});cursor=i.end}
 if(cursor<duration-1e-7)result.push({start:cursor,end:duration,text:''});return result;
}
export function splitInterval(intervals,time,caret=null){
 const index=intervals.findIndex(i=>time>i.start+0.0001&&time<i.end-0.0001);
 if(index<0)throw Error('请把光标放在区间内部，不能在已有边界上增加边界。');
 const i=intervals[index],at=caret===null?i.text.length:Math.max(0,Math.min(caret,i.text.length));
 return {index:index+1,intervals:[...intervals.slice(0,index),{...i,end:time,text:i.text.slice(0,at)},{...i,start:time,text:i.text.slice(at)},...intervals.slice(index+1)]};
}
export function removeLeftBoundary(intervals,index){
 if(index<=0||index>=intervals.length)throw Error('请选择内部边界；音频起止边界不能删除。');
 const left=intervals[index-1],right=intervals[index];
 const text=left.text===right.text?left.text:left.text+right.text;
 return {index:index-1,intervals:[...intervals.slice(0,index-1),{start:left.start,end:right.end,text},...intervals.slice(index+1)]};
}

export function moveTierBoundary(intervals,index,time){
 if(index<=0||index>=intervals.length)throw Error('音频首尾边界固定。');
 const left=intervals[index-1],right=intervals[index],shared=Math.abs(left.end-right.start)<1e-6;
 if(!Number.isFinite(time))throw Error('无效边界时间。');
 const minimum=shared?left.start+.001:left.end,maximum=right.end-.001;
 if(minimum>=maximum)return intervals.map(i=>({...i}));
 const value=Math.max(minimum,Math.min(maximum,time));
 return intervals.map((i,k)=>k===index?{...i,start:value}:shared&&k===index-1?{...i,end:value}:i);
}
export function visibleTicks(start,end,width){
 const desired=(end-start)*72/Math.max(width,1),scale=Math.pow(10,Math.floor(Math.log10(Math.max(desired,.0001))));
 const step=([1,2,5,10].find(n=>n*scale>=desired)||10)*scale,ticks=[];
 for(let t=Math.ceil((start-1e-8)/step)*step;t<=end+1e-8&&ticks.length<200;t+=step){const time=Number(t.toFixed(6));ticks.push({time,position:(time-start)/(end-start)*100,label:time.toFixed(Math.max(0,Math.min(4,-Math.floor(Math.log10(step)))))});}
 return ticks;
}
