"""Browser playback derivatives; source research recordings are read-only."""
import hashlib
import os
import threading
import uuid
from pathlib import Path
import av
from . import storage

_lock = threading.Lock()

def playback_wav(source):
    source = Path(source)
    stat = source.stat()
    key = hashlib.sha256(f'{source.resolve()}:{stat.st_size}:{stat.st_mtime_ns}:pcm-v1'.encode()).hexdigest()
    cache = Path(os.getenv('SPEECH_REVIEW_PLAYBACK_CACHE',str(storage.DATA/'playback_cache')))
    target = cache / (key + '.wav')
    with _lock:
        if target.exists():
            return target
        cache.mkdir(parents=True, exist_ok=True)
        temp = cache / (key + '.' + uuid.uuid4().hex + '.tmp')
        try:
            with av.open(str(source)) as src:
                if not src.streams.audio:
                    raise ValueError('文件中没有音频轨道')
                track = src.streams.audio[0]
                rate = track.codec_context.sample_rate
                layout = track.codec_context.layout.name
                with av.open(str(temp), 'w', format='wav') as dest:
                    out = dest.add_stream('pcm_s16le', rate=rate)
                    out.layout = layout
                    resampler = av.AudioResampler(format='s16', layout=layout, rate=rate)
                    for frame in src.decode(track):
                        for converted in resampler.resample(frame):
                            converted.pts = None
                            for packet in out.encode(converted):
                                dest.mux(packet)
                    for converted in resampler.resample(None):
                        converted.pts = None
                        for packet in out.encode(converted):
                            dest.mux(packet)
                    for packet in out.encode(None):
                        dest.mux(packet)
            os.replace(temp, target)
        except Exception as exc:
            temp.unlink(missing_ok=True)
            raise ValueError(f'无法生成播放副本：{source.name}；{exc}') from exc
    return target
