# Speech Review

Whisper transcription, audio review, Montreal Forced Aligner alignment, and editable TextGrid boundaries in one workspace.

## Google Colab

Upload **SpeechReview_Colab_Public.ipynb** to Colab and run the cells in order. The Public URL opens the complete interface in a separate browser tab. Use the generated username and password. The URL expires when the runtime stops. See [Colab instructions](Colab-Public-使用说明.md).

This repository includes source code and the built frontend, with no recordings, transcripts, saved reviews, model weights, or local environments. Dependencies and MFA models are downloaded separately. Colab deployment still needs validation in a real Colab session.

# 本地复听工作台 — 转写、复听与 MFA/TextGrid

界面按复听卡片排列：波形、播放／定位／缩放、Whisper 模型原文与候选诊断、折叠原 TXT、预填复听结论、Save、人工标签、备注、完成标记。

## Windows 安装和启动

需要 Python 3.11 或 3.12；Node.js 仅在重新构建前端时需要。解压整个文件夹，在该目录打开 PowerShell：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8765
```

打开 http://127.0.0.1:8765 。关闭终端中的服务用 Ctrl+C。已附带构建好的 frontend/dist。

也可以在依赖安装完成后运行 `powershell -ExecutionPolicy Bypass -File .\start.ps1`。

## 使用

1. 粘贴直接包含 WAV/TXT 的受试者文件夹完整路径，点击导入。支持大小写后缀；按文件主名匹配 TXT，保留原 TXT 文件名（包括大小写）。当前不递归子目录，避免同名文件冲突。
2. 文件名中的 number/nonhomo/homo 自动判断条件；无法判断时可在导入前手动指定。不确定条件时不会套用词表异常规则。
3. 单条或批量运行 Whisper。首次可能需要联网下载模型，音频不上传。按原 notebook：Number/Homo 优先 GPU medium/float16；Non-homo 优先 GPU large-v3/float16；不可用时回退 CPU medium/int8。需要 GPU 时安装兼容的 CUDA 环境。
4. 第一次识别的文字按 token 空格分隔后预填复听结论；模型原文独立保存。修改或直接确认后点击 Save。勾选完成和修改标签后也需要 Save。
5. 导出已保存 TXT ZIP，解压后 TXT 名字与原 TXT 一致。尚未保存的模型预填不纳入导出。标签、备注只进入本地元数据和 QC CSV。

## 数据位置与恢复

源 WAV/TXT 只读取。应用目录中的 `data/<项目ID>/project.json` 保存参考文本快照、ASR、ASR 历史、人工修订历史、标签和备注；`corrected/` 存同名人工修订 TXT。请备份整个 data 目录。源 WAV 以原路径访问，移动后需要恢复原路径。可通过 SPEECH_REVIEW_DATA 环境变量指定独立数据目录（勿设置为源数据目录）。

重新导入相同目录会打开原项目；关闭服务后数据保留。批量转写只处理尚无 ASR 的条目。重跑单条识别不覆盖已 Save 的人工文字和标签；前端阻止有未保存修改时切换项目、重跑该条或导出。

## Notebook 复用说明（已按原代码恢复）

`backend/notebook_code/number.py`、`homo.py`、`nonhomo.py` 分别从用户 notebook 第 9、18、19 单元（零起始索引）原样抽取常量和函数。未执行原 main()、安装命令或源文件写入代码。manifest.json 保存原 notebook SHA-256 和抽取符号清单。

- Number：原数字任务提示词，language=zh、vad_filter=True，其他解码参数不额外指定，与原脚本一致。
- Homo：原提示词，temperature=0、beam_size=5、best_of=5、condition_on_previous_text=False。
- Non-homo：原提示词，beam_size=5、temperature=0、condition_on_previous_text=False。
- 词表、映射、pypinyin 分类、原始 QC 判断均直接调用抽取函数。Number 原脚本遗漏 ALLOW_MISC 定义，采用 Homo 中已有定义补齐；Number 的宽泛自我纠正规则保留，并在 UI 明示可能误报正常数字序列。
- GPU/CPU 模型选择按原脚本执行；无 CUDA 设备时直接进入原有 CPU 回退分支，避免无效下载。音频读取使用兼容 PyAV 的独立解码器，提供相同目标采样率的单声道样本给 faster-whisper。

按用户确认：复听结论预填原始转写分词结果；Homo 映射、Non-homo 预处理／映射／去重结果只在“原脚本处理结果”中展示。点击“采用脚本结果到复听结论”才进入编辑框，仍需 Save。原始 ASR、脚本结果、人工文字分别保留。旧版通用流程结果会标为需重跑，历史保留。

文字规则不能证明实际发音错误，空 ASR 不能证明静音；所有标记只供复听参考。原脚本的自动源 TXT 覆盖未接入。

## MFA 强制对齐、人工边界和 TextGrid

本机已准备独立 MFA 3.3.10 运行环境和 mandarin_mfa / mandarin_china_mfa 模型。分发 ZIP 不包含大型运行环境或研究数据；在另一台 Windows 电脑上可运行：

```powershell
.\.venv\Scripts\python.exe install_mfa.py
```

安装过程从官方 micromamba 与 conda-forge 下载约数百 MB 的包，仅写入项目 runtime/。不修改全局 Conda 或 PowerShell 配置。首次对齐自动下载普通话模型到 data/mfa_models/。已有 MFA 可设置 MFA_EXECUTABLE 为可执行文件；可通过 MFA_ROOT_DIR 指定模型目录。

使用顺序：

1. 复听修改转写，token 之间用空格分隔，点击 Save。空文本不做强制对齐。
2. 单条点击“强制对齐已保存文本”，或顶部“一键对齐已保存条目”。批量跳过已有有效对齐的条目。输入只取人工 Save 的 corrected 字段，不取 Whisper 或原 TXT。
3. 对齐完成后，上方波形显示字词区间。点击区间复听；拖动左右边界，或在时间表中输入开始、结束秒数。也可撤销／放弃未保存边界。
4. 点击“保存人工边界”。自动版与人工版可切换，重跑 MFA 仅更新自动版。每版保留历史和独立 artifact。
5. 下载单条或全部真实 Praat TextGrid；包含 words IntervalTier，完整音频边界与空白静音间隔。文件名为原主名加 _auto.TextGrid / _reviewed.TextGrid。
6. 可在 Praat 进一步调整，保存后从卡片导入 TextGrid，支持长／短格式与 UTF-8/UTF-16。必须有一个 words 层，字词次序与已保存转写一致，时长与完整音频相符。

修改转写文字或源音频后，原对齐显示过期。过期版本及历史仍保存，下载和批量导出仅纳入有效版本。出现 OOV、缺词、合词或 token 不一致会报错，不能通过均分时间、复制 Whisper 时间戳或静默删除填充词代替真实对齐。需先修正文本／MFA 词典后重试。

边界编辑校验禁止越界、零长度、倒序及重叠。自动边界仍需人工核查后用于声学研究。本版未实现频谱、音高曲线和直接控制 Praat。

导出全部资料包含 corrected_txt/、textgrids/、report.csv、alignment.csv、export-info.json。alignment.csv 有 filename/version/word/start/end。报告备注不写入转写 TXT。

日志与数据：data/<项目ID>/alignment_runs/<runID>/mfa.log 保存每次对齐日志；textgrids/versions/ 保存版本文件；project.json 保留 auto/reviewed 及 alignment_history；data/alignment_jobs/ 保存进度。服务重启后未完成任务标为中断，可重新提交。

参考：[MFA 安装](https://montreal-forced-aligner.readthedocs.io/en/v3.3.2/installation.html)、[MFA 对齐](https://montreal-forced-aligner.readthedocs.io/en/v3.3.7/user_guide/workflows/alignment.html)、[micromamba 官方安装](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html)。

## 播放和 Whisper 更新

支持扩展名为 WAV、内部格式为 AIFF 的录音。网页播放副本存入 data/playback_cache，保留原采样率与时长，不修改原始文件。Whisper 使用应用独立解码得到 16 kHz 单声道浮点样本，避免新版 PyAV 移除 metadata_errors 参数引起的转写失败。

“一键运行全部 Whisper”按顺序处理当前项目所有尚未转写的录音；失败条目仍可重试。顶部显示模型加载、当前文件、处理进度、耗时和错误详情。刷新恢复最近打开的项目及任务状态；服务重启会将旧任务标为中断，点击继续只处理未完成的录音。识别结果自动预填，仍需人工复听并 Save 后才导出。

## 开发及测试

```powershell
cd frontend
npm install
npm run build
cd ..
.\.venv\Scripts\python.exe -m pip install httpx
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

测试覆盖源 TXT 保护、ASR 重跑保护、重复及填充词保留、重新导入恢复、未保存不导出、ZIP 同名与内容一致，以及浏览器跨源写入拦截。ASR 测试使用替身，真实模型需用研究录音另行验收。

## 一键保存所有 TXT
顶部按钮保存全部卡片当前的复听结论、标签和备注（包括未点击单条 Save 的编辑和筛选隐藏条目）。未转写且无文字的条目跳过；有模型结果或手工静音标签的空文本可保存。不会自动标记完成，也不会改动原 TXT。保存后仍需点击 MFA 对齐，等待生成后才能导出 TextGrid；没有有效对齐时会显示提示，不再下载空 ZIP。


## 独立在线边界编辑工作区
顶部‘对齐与边界编辑’标签集中显示单条录音、波形、已保存文本和边界表。可在新浏览器标签打开 /?view=alignment。选择录音或上一条／下一条读取已保存自动版／人工版，也可导入已有 TextGrid。共用边界联动、点击区间复听、数值编辑、撤销及保存人工版均保留。波形缩放支持最高约 64 倍。当前页面切换工作区／录音保留未保存边界，但新浏览器标签只读取已经保存到后台的版本。


## 在 VS Code 运行
在 VS Code 打开整个 speech-review 文件夹，选择项目 .venv 解释器。已提供 .vscode/launch.json：F5 启动本地工作台，Shift+F5 停止；输出在 Debug Console，支持 Python 断点调试。默认端口 8765，启动前关闭占用此端口的旧服务。‘Run project tests’任务可运行项目测试。


## Google Colab 版本
另有独立的 SpeechReview_Colab.ipynb，内置程序代码。上传到 Colab 后按步骤安装 Python、Linux MFA，选择上传录音 ZIP 或 Drive 文件夹，再以内嵌方式使用原工作台。完整 Web UI 适用于允许此用法且有可用额度的 Pro 等运行时；不创建公共隧道或自动保活。原 notebook 提示词和参数保持不变。临时文件和模型留在 Colab 磁盘，可选把输入与项目修订保存到自己的 Drive。内嵌版禁用新窗口链接，允许在浏览器存储不可用时继续选择项目。iPad 触控和 Colab 云端端到端执行仍需实机验收。
