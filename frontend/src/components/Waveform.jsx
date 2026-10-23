import {useLanguage} from '../i18n';
import React, { useEffect, useRef, useState } from 'react';
import WaveSurfer from 'wavesurfer.js';
import Regions from 'wavesurfer.js/dist/plugins/regions.esm.js';
import WaveNavigation from './WaveNavigation';
export default function Waveform({ url, intervals = [], editable = false, onIntervalsChange, onReady, onCursorChange, onPlaybackPause, editCursor, onSelectInterval, onKeyDown, selectedIndex, height = 88, visible = true }) {
    const { tr } = useLanguage();
    const regions = useRef(), latest = useRef();
    latest.current = { intervals, onIntervalsChange, onReady, onCursorChange, onPlaybackPause, onSelectInterval, editable };
    const [boundaryTime, setBoundaryTime] = useState(null);
    const [selection, setSelection] = useState(null), selectionRef = useRef(null), selectionRegion = useRef(null), renderSelection = useRef(() => { });
    const container = useRef(), wave = useRef();
    const [ready, setReady] = useState(false), [playing, setPlaying] = useState(false), [time, setTime] = useState(0), [duration, setDuration] = useState(0), [error, setError] = useState(''), [attempt, setAttempt] = useState(0);
    useEffect(() => {
        let alive = true;
        const controller = new AbortController();
        setReady(false);
        setError('');
        setPlaying(false);
        setTime(0);
        setDuration(0);
        setSelection(null);
        selectionRef.current = null;
        selectionRegion.current = null;
        const ws = WaveSurfer.create({ container: container.current, height, waveColor: '#537f88', progressColor: '#183f48', cursorColor: '#dc3545', cursorWidth: 2, normalize: true, interact: true });
        wave.current = ws;
        const plugin = ws.registerPlugin(Regions.create());
        regions.current = plugin;
        // Listen in capture phase so a drag can cross existing word regions. Boundary
        // handles retain their normal resize gesture; selection never edits labels.
        const wrapper = ws.getWrapper();
        let drag = null, suppressClickUntil = 0, playbackActive = false;
        const style = document.createElement('style');
        style.textContent = '[part~="region"]{border-left:1px solid #79959b;border-right:0!important;box-sizing:border-box}[part~="region-handle"]{width:6px!important;opacity:.6;border-color:#79959b!important}[part~="region-handle"]:hover{opacity:1;background:rgba(38,112,141,.2)}';
        wrapper.getRootNode().appendChild(style);
        style.textContent += '[part="cursor"]{z-index:30!important;pointer-events:none!important;box-shadow:0 0 0 1px #fff9}';
        const timeAt = event => { const rect = wrapper.getBoundingClientRect(); return Math.max(0, Math.min(ws.getDuration(), (event.clientX - rect.left) / rect.width * ws.getDuration())); };
        renderSelection.current = () => { const range = selectionRef.current; if (!range)
            return; if (selectionRegion.current && !selectionRegion.current.isRemoved)
            selectionRegion.current.setOptions(range);
        else {
            selectionRegion.current = plugin.addRegion({ id: 'playback-selection', ...range, color: 'rgba(85,125,235,.32)', drag: false, resize: false });
            selectionRegion.current.element.style.pointerEvents = 'none';
            selectionRegion.current.element.style.zIndex = '8';
        } };
        const clearSelection = () => { selectionRegion.current?.remove(); selectionRegion.current = null; selectionRef.current = null; setSelection(null); };
        const down = event => { if (event.button !== 0 || !ws.getDuration() || event.pointerType === 'touch')
            return; if (event.composedPath().some(node => node.getAttribute?.('part')?.includes('region-handle')))
            return; event.stopImmediatePropagation(); clearSelection(); drag = { id: event.pointerId, x: event.clientX, start: timeAt(event), moved: false }; };
        const move = event => { if (!drag || event.pointerId !== drag.id)
            return; if (!drag.moved && Math.abs(event.clientX - drag.x) < 4)
            return; if (!drag.moved) {
            drag.moved = true;
            ws.pause();
            wrapper.setPointerCapture(event.pointerId);
        } event.preventDefault(); event.stopImmediatePropagation(); const end = timeAt(event); const range = { start: Math.min(drag.start, end), end: Math.max(drag.start, end) }; selectionRef.current = range; setSelection(range); renderSelection.current(); };
        const up = event => { if (!drag || event.pointerId !== drag.id)
            return; const wasDragging = drag.moved; drag = null; if (!wasDragging)
            return; event.preventDefault(); event.stopImmediatePropagation(); suppressClickUntil = performance.now() + 400; if (wrapper.hasPointerCapture(event.pointerId))
            wrapper.releasePointerCapture(event.pointerId); container.current.closest('.wave')?.focus(); const range = selectionRef.current; if (range && range.end - range.start > .001)
            ws.play(range.start, range.end).catch(e => { if (alive)
                setError(e.message); }); };
        const cancel = () => { drag = null; clearSelection(); };
        const click = event => { if (performance.now() < suppressClickUntil) {
            event.preventDefault();
            event.stopImmediatePropagation();
        } };
        wrapper.addEventListener('pointerdown', down, true);
        wrapper.addEventListener('pointermove', move, true);
        wrapper.addEventListener('pointerup', up, true);
        wrapper.addEventListener('pointercancel', cancel, true);
        wrapper.addEventListener('click', click, true);
        plugin.on('region-clicked', (region, event) => { event.stopPropagation(); if (!region.id.startsWith('w'))
            return; const rect = region.element.getBoundingClientRect(); const time = region.start + Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)) * (region.end - region.start); latest.current.onSelectInterval?.(Number(region.id.slice(1)), time); container.current.closest('.wave')?.focus(); if (event.shiftKey) { ws.pause(); ws.setTime(time); latest.current.onCursorChange?.(time); return; } ws.play(region.start, region.end).catch(e => { if (alive)
            setError(e.message); }); });
        plugin.on('region-update', (region, side) => { if (region.id.startsWith('w') && side)
            setBoundaryTime(region[side]); });
        plugin.on('region-updated', region => { setBoundaryTime(null); const idx = Number(region.id.slice(1)), current = latest.current.intervals, original = current[idx]; if (!original)
            return; const previous = current[idx - 1], next = current[idx + 1]; const linkLeft = previous && Math.abs(previous.end - original.start) < 1e-6, linkRight = next && Math.abs(next.start - original.end) < 1e-6; const start = !previous ? 0 : Math.max(previous ? (linkLeft ? previous.start + .001 : previous.end) : 0, region.start), end = !next ? ws.getDuration() : Math.min(next ? (linkRight ? next.end - .001 : next.start) : ws.getDuration(), region.end); if (end <= start) {
            region.setOptions({ start: original.start, end: original.end });
            return;
        } latest.current.onIntervalsChange?.(current.map((i, k) => k === idx ? { ...i, start, end } : linkLeft && k === idx - 1 ? { ...i, end: start } : linkRight && k === idx + 1 ? { ...i, start: end } : i)); });
        ws.on('interaction', time => { latest.current.onCursorChange?.(time); });
        ws.on('ready', () => { if (alive) {
            setReady(true);
            setDuration(ws.getDuration());
            latest.current.onReady?.(ws);
        } });
        ws.on('timeupdate', setTime);
        ws.on('play', () => { playbackActive = true; setPlaying(true); });
        ws.on('pause', () => { setPlaying(false); setTime(ws.getCurrentTime()); if (playbackActive) latest.current.onPlaybackPause?.(ws.getCurrentTime()); playbackActive = false; });
        ws.on('error', e => { if (alive)
            setError(e.message); });
        // Fetch a fresh PCM derivative, then play a blob. This avoids cached source
        // media responses and browser range-cache reuse from earlier app versions.
        (async () => { try {
            const response = await fetch(url + '?playback=pcm-v2&retry=' + attempt, { cache: 'no-store', signal: controller.signal });
            if (!response.ok) {
                const body = await response.json().catch(() => ({}));
                throw Error(body.detail || tr("\u97F3\u9891\u8BF7\u6C42\u5931\u8D25 ({0})", [response.status]));
            }
            const data = await response.arrayBuffer();
            const header = new TextDecoder('ascii').decode(data.slice(0, 12));
            if (!header.startsWith('RIFF') || !header.endsWith('WAVE'))
                throw Error(tr("\u670D\u52A1\u672A\u8FD4\u56DE\u6807\u51C6 WAV\uFF0C\u8BF7\u91CD\u65B0\u542F\u52A8\u672C\u5730\u670D\u52A1"));
            if (alive)
                await ws.loadBlob(new Blob([data], { type: 'audio/wav' }));
        }
        catch (e) {
            if (alive && e.name !== 'AbortError')
                setError(e.message);
        } })();
        return () => { alive = false; controller.abort(); wrapper.removeEventListener('pointerdown', down, true); wrapper.removeEventListener('pointermove', move, true); wrapper.removeEventListener('pointerup', up, true); wrapper.removeEventListener('pointercancel', cancel, true); wrapper.removeEventListener('click', click, true); renderSelection.current = () => { }; style.remove(); ws.destroy(); };
    }, [url, attempt]);
    useEffect(() => { if (!ready || !regions.current)
        return; regions.current.clearRegions(); intervals.forEach((i, k) => { if (Number.isFinite(i.start) && Number.isFinite(i.end) && i.start >= 0 && i.end > i.start && i.end <= duration)
        regions.current.addRegion({ id: 'w' + k, start: i.start, end: i.end, color: k === selectedIndex ? 'rgba(247,207,83,.12)' : 'transparent', drag: false, resize: editable, resizeStart: k > 0, resizeEnd: k < intervals.length - 1, minLength: .001 }); }); renderSelection.current(); }, [intervals, editable, ready, duration, selectedIndex]);
    useEffect(() => { wave.current?.setOptions({ height }); }, [height]);
    useEffect(() => { if (!visible)
        wave.current?.pause(); }, [visible]);
    useEffect(() => { if (ready && !playing && Number.isFinite(editCursor) && Math.abs(wave.current.getCurrentTime() - editCursor) > .0001) wave.current.setTime(editCursor); }, [editCursor, ready, playing]);
    function clearPlaybackSelection() { selectionRegion.current?.remove(); selectionRegion.current = null; selectionRef.current = null; setSelection(null); }
    function playSelected() { const item = intervals[selectedIndex]; if (!item)
        return; clearPlaybackSelection(); wave.current.play(item.start, item.end).catch(e => setError(e.message)); }
    function togglePlay() { const ws = wave.current; if (playing)
        ws.pause();
    else {
        const range = selectionRef.current;
        (range ? ws.play(range.start, range.end) : ws.play()).catch(e => setError(e.message));
    } }
    return <section className="wave" tabIndex={0} onKeyDown={event => { if (event.key === ' ' && !event.target.matches('input,textarea,button')) {
        event.preventDefault();
        event.stopPropagation();
        togglePlay();
    }
    else
        onKeyDown?.(event); }}><WaveNavigation ws={wave.current} ready={ready} duration={duration} time={time} intervals={intervals} selectedIndex={selectedIndex} editable={editable} onSelectInterval={onSelectInterval} onIntervalsChange={onIntervalsChange} selection={selection} onClearSelection={clearPlaybackSelection} detailed={height >= 140}><div className="wave-canvas" ref={container}/></WaveNavigation>{boundaryTime !== null && <div className="boundary-time-hint" role="status">{tr("\u8FB9\u754C")}{boundaryTime.toFixed(3)}{tr("\u79D2")}</div>}{error ? <div className="error"><p>{tr("\u97F3\u9891\u52A0\u8F7D\u5931\u8D25\uFF1A")}{tr(error)}</p><button onClick={() => setAttempt(a => a + 1)}>{tr("\u91CD\u65B0\u52A0\u8F7D\u97F3\u9891")}</button></div> : <><div className="audio-controls"><button disabled={!ready} onClick={togglePlay}>{playing ? tr("\u2161 \u6682\u505C") : ready ? selection ? tr("\u25B6 \u64AD\u653E\u9009\u533A") : tr("\u25B6 \u64AD\u653E") : tr("\u52A0\u8F7D\u97F3\u9891\u2026")}</button>{intervals[selectedIndex] && <button disabled={!ready} onClick={playSelected} title={tr("\u64AD\u653E\u9009\u4E2D\u5B57\u8BCD\u7684\u5DE6\u53F3\u8FB9\u754C\u4E4B\u95F4\uFF1B\u4E5F\u53EF\u6309\u7A7A\u683C")}>{tr("\u25B6 \u64AD\u653E\u9009\u4E2D\u5B57\u8BCD")}</button>}<span className="playback-position">{time.toFixed(3)} / {duration.toFixed(1)}{tr("\u79D2")}</span></div><p className="hint cursor-help">{tr("红色竖线是播放／编辑光标；暂停后停在当前位置，Enter 增加边界。Shift + 单击只定位、不播放；空格播放／暂停。")}</p><p className="hint">{tr("\u5355\u51FB\u6CE2\u5F62\u533A\u95F4\u5373\u64AD\u653E\u4E24\u6761\u8FB9\u754C\u4E4B\u95F4\uFF1B\u7A7A\u683C\u6216\u64AD\u653E\u9009\u4E2D\u5B57\u8BCD\u53EF\u91CD\u64AD\u3002\u9F20\u6807\u62D6\u9009\u64AD\u653E\u4EFB\u610F\u8303\u56F4\uFF0C\u8FB9\u754C\u624B\u67C4\u4ECD\u7528\u4E8E\u8C03\u6574\u65F6\u95F4\u3002")}</p>{selection && <div className="selection-info" role="status" data-start={selection.start} data-end={selection.end}>{tr("\u9009\u533A")}{selection.start.toFixed(3)}–{selection.end.toFixed(3)}{tr("\u79D2\uFF08")}{(selection.end - selection.start).toFixed(3)}{tr("\u79D2\uFF09")}<button onClick={() => { selectionRegion.current?.remove(); selectionRegion.current = null; selectionRef.current = null; setSelection(null); }}>{tr("\u6E05\u9664\u9009\u533A")}</button></div>}</>}</section>;
}
