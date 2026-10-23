import {useLanguage} from '../i18n';
import React, { useEffect, useRef, useState } from 'react';
import { moveTierBoundary, visibleTicks } from '../alignmentEditing';
// Navigation and annotation share the main player's exact visible time window.
export default function WaveNavigation({ ws, ready, duration, time, intervals, selectedIndex, editable, onSelectInterval, onIntervalsChange, selection, onClearSelection, detailed, children }) {
    const { tr } = useLanguage();
    const [view, setView] = useState({ start: 0, end: 1, width: 1 }), viewRef = useRef(view);
    viewRef.current = view;
    const [zoom, setZoom] = useState(0), [preview, setPreview] = useState(null), [hint, setHint] = useState(null);
    const canvas = useRef(), overview = useRef(), overviewDrag = useRef(), tier = useRef(), tierDrag = useRef(), current = useRef();
    current.current = { intervals, onIntervalsChange, onSelectInterval };
    useEffect(() => {
        if (!ws || !ready)
            return;
        let peaks = ws.exportPeaks({ channels: 1, maxLength: 1400 })[0];
        const paint = () => {
            const element = canvas.current, width = element?.clientWidth;
            if (!width || !peaks.length)
                return;
            const ratio = window.devicePixelRatio || 1;
            element.width = Math.round(width * ratio);
            element.height = 38 * ratio;
            const context = element.getContext('2d');
            context.scale(ratio, ratio);
            context.clearRect(0, 0, width, 38);
            context.strokeStyle = '#668c94';
            context.beginPath();
            const max = Math.max(.001, ...peaks.map(Math.abs));
            for (let x = 0; x < width; x++) {
                const h = Math.abs(peaks[Math.min(peaks.length - 1, Math.floor(x / width * peaks.length))]) / max * 16;
                context.moveTo(x, 19 - h);
                context.lineTo(x, 19 + h);
            }
            context.stroke();
        };
        const sync = () => { const full = ws.getWrapper().scrollWidth, width = ws.getWidth(), d = ws.getDuration(); if (!full || !width || !d)
            return; const next = { start: ws.getScroll() / full * d, end: Math.min(d, (ws.getScroll() + width) / full * d), width }; viewRef.current = next; setView(old => Math.abs(old.start - next.start) < 1e-6 && Math.abs(old.end - next.end) < 1e-6 && old.width === width ? old : next); };
        const observer = new ResizeObserver(() => { sync(); paint(); });
        observer.observe(ws.getWrapper().parentElement);
        const off = [ws.on('scroll', sync), ws.on('redraw', sync), ws.on('zoom', value => { sync(); setZoom(value > 0 ? Math.max(0, Math.min(6, Math.log2(value * duration / ws.getWidth()))) : 0); })];
        sync();
        paint();
        return () => { observer.disconnect(); off.forEach(fn => fn()); peaks = []; };
    }, [ws, ready, duration, detailed]);
    const span = Math.max(.000001, view.end - view.start), ticks = visibleTicks(view.start, view.end, view.width), shown = preview ?? intervals;
    function panTo(time) { if (!ready)
        return; ws.setScrollTime(Math.max(0, Math.min(duration - (viewRef.current.end - viewRef.current.start), time))); }
    function changeZoom(value) { if (!ready)
        return; setZoom(value); ws.zoom(value === 0 ? 0 : ws.getWidth() / duration * Math.pow(2, value)); }
    function showAll() { changeZoom(0); ws?.setScroll(0); }
    function zoomSelection() { if (!selection || !ready)
        return; const length = Math.max(.001, selection.end - selection.start); changeZoom(Math.log2(Math.min(64, Math.max(1, duration / (length * 1.08))))); panTo(Math.max(0, selection.start - length * .04)); }
    function overviewDown(e) { if (!ready || e.button !== 0)
        return; e.preventDefault(); e.currentTarget.setPointerCapture(e.pointerId); const rect = overview.current.getBoundingClientRect(), time = (e.clientX - rect.left) / rect.width * duration, v = viewRef.current; const offset = time >= v.start && time <= v.end ? time - v.start : (v.end - v.start) / 2; overviewDrag.current = { id: e.pointerId, offset }; panTo(time - offset); }
    function overviewMove(e) { const drag = overviewDrag.current; if (!drag || drag.id !== e.pointerId)
        return; const rect = overview.current.getBoundingClientRect(); panTo((e.clientX - rect.left) / rect.width * duration - drag.offset); }
    function paintBoundaries(next) { setPreview(next); const plugin = ws?.getActivePlugins().find(p => typeof p.getRegions === 'function'); for (const region of plugin?.getRegions() ?? []) {
        if (region.id.startsWith('w')) {
            const item = next[Number(region.id.slice(1))];
            if (item)
                region.setOptions({ start: item.start, end: item.end });
        }
    } }
    function tierDown(e, index) { if (!editable || e.button !== 0)
        return; e.preventDefault(); e.stopPropagation(); onClearSelection(); e.currentTarget.setPointerCapture(e.pointerId); tierDrag.current = { id: e.pointerId, index, original: intervals, next: null }; setHint(intervals[index].start); }
    function tierMove(e) { const drag = tierDrag.current; if (!drag || drag.id !== e.pointerId)
        return; const rect = tier.current.getBoundingClientRect(), v = viewRef.current, at = v.start + (e.clientX - rect.left) / rect.width * (v.end - v.start); drag.next = moveTierBoundary(drag.original, drag.index, at); paintBoundaries(drag.next); setHint(drag.next[drag.index].start); }
    function tierUp(e, cancel = false) { const drag = tierDrag.current; if (!drag || drag.id !== e.pointerId)
        return; tierDrag.current = null; setHint(null); if (e.currentTarget.hasPointerCapture(e.pointerId))
        e.currentTarget.releasePointerCapture(e.pointerId); if (cancel)
        paintBoundaries(drag.original);
    else {
        if (drag.next)
            current.current.onIntervalsChange?.(drag.next);
        current.current.onSelectInterval?.(drag.index, (drag.next ?? drag.original)[drag.index].start);
    } setPreview(null); }
    function play(item, index) { onClearSelection(); onSelectInterval?.(index, item.start); ws.play(item.start, item.end).catch(() => { }); }
    return <>
  <div className="wave-navigation" hidden={!detailed}><div className="wave-view-heading"><span>{tr("\u6574\u6BB5\u6982\u89C8")}<small>{tr("\u62D6\u52A8\u7A97\u53E3\u67E5\u770B")}</small></span><span className="visible-time" data-start={view.start} data-end={view.end}>{tr("\u5F53\u524D")}{view.start.toFixed(3)}–{view.end.toFixed(3)}{tr("\u79D2 / \u5171")}{duration.toFixed(3)}{tr("\u79D2")}</span></div>
   <div ref={overview} className="wave-overview" role="slider" aria-label={tr("\u6574\u6BB5\u6982\u89C8\u5B9A\u4F4D")} aria-valuemin={0} aria-valuemax={Math.max(0, duration - span)} aria-valuenow={view.start} tabIndex={ready ? 0 : -1} onPointerDown={overviewDown} onPointerMove={overviewMove} onPointerUp={() => { overviewDrag.current = null; }} onPointerCancel={() => { overviewDrag.current = null; }} onKeyDown={e => { if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) {
        e.preventDefault();
        e.stopPropagation();
        panTo(e.key === 'Home' ? 0 : e.key === 'End' ? duration : view.start + (e.key === 'ArrowLeft' ? -1 : 1) * span / 5);
    } }}>
    <canvas ref={canvas} aria-hidden="true"/><div className="overview-window" style={{ left: `${view.start / Math.max(duration, .001) * 100}%`, width: `${Math.min(100, span / Math.max(duration, .001) * 100)}%` }}/><div className="overview-playhead" style={{ left: `${time / Math.max(duration, .001) * 100}%` }}/>
   </div>
  </div>
  {children}
  {ready && <div className="wave-time-axis" aria-label={tr("\u65F6\u95F4\u523B\u5EA6\uFF08\u79D2\uFF09")}>{ticks.map(tick => <span key={tick.time} style={{ left: `${tick.position}%` }}>{tick.label}</span>)}<small>{tr("\u79D2")}</small></div>}
  {ready && intervals.length > 0 && <><div className="tier-heading"><span>{tr("\u5B57\u8BCD\u5C42 \u00B7 \u5355\u51FB\u590D\u542C")}</span><span><i className="selected-legend"/>{tr("\u9009\u4E2D\u5B57\u8BCD")}<i className="range-legend"/>{tr("\u64AD\u653E\u9009\u533A")}</span></div>
   <div ref={tier} className="wave-text-tier" aria-label={tr("\u4E0E\u6CE2\u5F62\u540C\u6B65\u7684\u5B57\u8BCD\u5C42")}>{shown.map((item, index) => {
                if (item.end <= view.start || item.start >= view.end)
                    return null;
                const start = Math.max(view.start, item.start), end = Math.min(view.end, item.end);
                return <React.Fragment key={index}><button className={'tier-cell ' + (selectedIndex === index ? 'selected' : '') + (!item.text ? ' empty' : '')} aria-label={tr("\u5B57\u8BCD\u5C42 {0} {1}", [index + 1, item.text || tr("\u7A7A\u767D")])} title={tr("{0} \u00B7 {1}\u2013{2} \u79D2 \u00B7 \u5355\u51FB\u590D\u542C", [item.text || tr("\u7A7A\u767D"), item.start.toFixed(3), item.end.toFixed(3)])} style={{ left: `${(start - view.start) / span * 100}%`, width: `${(end - start) / span * 100}%` }} onClick={() => play(item, index)}>{item.text || '·'}</button>
     {editable && index > 0 && item.start >= view.start && item.start <= view.end && <div role="separator" aria-label={tr("\u5B57\u8BCD\u5C42\u8FB9\u754C {0}", [index + 1])} aria-orientation="vertical" className="tier-boundary-handle" title={tr("\u62D6\u52A8\u8FB9\u754C {0} \u79D2", [item.start.toFixed(3)])} style={{ left: `${(item.start - view.start) / span * 100}%` }} onPointerDown={e => tierDown(e, index)} onPointerMove={tierMove} onPointerUp={e => tierUp(e)} onPointerCancel={e => tierUp(e, true)}/>}</React.Fragment>;
            })}{time >= view.start && time <= view.end && <div className="tier-cursor" aria-hidden="true" data-time={time} style={{left: `${(time - view.start) / span * 100}%`}}/>}{selection && <div className="tier-playback-selection" style={{ left: `${(selection.start - view.start) / span * 100}%`, width: `${(selection.end - selection.start) / span * 100}%` }}/>}</div></>}
  {hint !== null && <div className="boundary-time-hint" role="status">{tr("\u8FB9\u754C")}{' '}{hint.toFixed(3)}{tr("\u79D2")}</div>}
  <div className="wave-zoom-toolbar"><button disabled={!ready || !selection} onClick={zoomSelection}>{tr("\u7F29\u653E\u5230\u9009\u533A")}</button><button disabled={!ready} onClick={showAll}>{tr("\u663E\u793A\u5168\u90E8")}</button><label>{tr("\u7F29\u653E")}<input aria-label={tr("\u6CE2\u5F62\u7F29\u653E")} type="range" min="0" max="6" step="0.25" value={zoom} disabled={!ready} onChange={e => changeZoom(Number(e.target.value))}/></label></div>
 </>;
}
