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
