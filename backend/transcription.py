import os
import threading

_models = {}
LOCK = threading.Lock()

def decode_audio(path):
    """Decode by content, including AIFF recordings carrying a .wav extension.

    Supply samples to faster-whisper rather than relying on its version-specific
    av.open(metadata_errors=...) call, removed in newer PyAV releases.
    """
    import av
    import numpy as np
    resampler = av.AudioResampler(format='fltp',layout='mono',rate=16000)
    parts=[]
    with av.open(str(path)) as container:
        if not container.streams.audio:
            raise ValueError('文件没有可读取的音频轨道')
        for frame in container.decode(audio=0):
            for converted in resampler.resample(frame):
                parts.append(converted.to_ndarray().reshape(-1))
        for converted in resampler.resample(None):
            parts.append(converted.to_ndarray().reshape(-1))
    if not parts:
        raise ValueError('音频为空')
    return np.concatenate(parts).astype(np.float32,copy=False)

def transcribe(path, progress=None, condition=None):
    from . import profiles
    condition=condition or profiles.infer_condition(str(path))
    options=profiles.parameters(condition)
    progress = progress or (lambda **values: None)
    # Call under LOCK: one model instance and one inference at a time.
    from faster_whisper import WhisperModel
    if condition not in _models:
        gpu_model='large-v3' if condition=='nonhomo' else 'medium'
        progress(stage='loading_model',message=f'按原 notebook 加载 {condition} 模型：优先 GPU {gpu_model}，失败回退 CPU medium')
        try:
            # The notebook uses a GPU-first try/except for both construction and
            # model download. Avoid downloading a GPU model on CPU-only machines.
            import ctranslate2
            if not ctranslate2.get_cuda_device_count():
                raise RuntimeError('未检测到 CUDA 设备')
            model=WhisperModel(gpu_model,device='cuda',compute_type='float16')
            model_name,device,compute=gpu_model,'cuda','float16'
        except Exception as exc:
            progress(stage='loading_model',message=f'GPU 不可用，按原 notebook 回退 CPU medium/int8：{exc}',model='medium',device='cpu')
            # Share the same medium CPU model between notebook conditions.
            cached=_models.get('_cpu_medium')
            model=cached[0] if cached else WhisperModel('medium',device='cpu',compute_type='int8')
            model_name,device,compute='medium','cpu','int8'
            _models['_cpu_medium']=(model,model_name,device,compute)
        _models[condition]=(model,model_name,device,compute)
    model,model_name,device,compute=_models[condition]
    progress(model=model_name,device=device,profile=condition)
    progress(stage='decoding_audio',message='正在读取音频')
    samples = decode_audio(path)
    progress(stage='transcribing',message='Whisper 正在识别，CPU 模式需要一些时间',audio_duration=len(samples)/16000,audio_seconds=0)
    segments, info = model.transcribe(samples, **options)
    result=[]
    for segment in segments:
        result.append(segment)
        progress(stage='transcribing',message='Whisper 正在识别',audio_seconds=segment.end)
    segments = result
    return {'raw':' '.join(s.text for s in segments),
        'notebook_raw':' '.join(s.text.strip() for s in segments).strip(),
        'segments':[{'start':s.start,'end':s.end,'text':s.text,'avg_logprob':s.avg_logprob} for s in segments],
        'avg_logprob':sum(s.avg_logprob for s in segments)/len(segments) if segments else None,
        'model':model_name,'device':device,'compute_type':compute,
        'profile':condition,'pipeline_version':profiles.PIPELINE_VERSION,'parameters':options}
