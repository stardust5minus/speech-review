# Colab 工作台试用

1. 下载同目录的 **SpeechReview_Colab.ipynb**。
2. 打开 https://colab.research.google.com/ ，选择 **File → Upload notebook**，上传这个文件。
3. 确认使用你的 Pro 账号，查看 Resources 面板是否有可用 compute units。可在 Runtime → Change runtime type 中选 GPU；资源可用性由 Colab 决定。
4. 从上到下运行单元。程序源码已内置；首次安装 MFA 和模型可能较慢。
5. 如需跨会话保留数据，把第 3 步的 `PERSIST_TO_DRIVE` 设为 True，并由你手动授权 Drive。否则文件只存在于临时运行时，退出前导出。
6. 上传一个受试者的录音 ZIP（WAV + 同名 TXT），或填写已挂载的 Drive 文件夹路径。不能使用原电脑的 C:\ 路径。
7. 在第 8 步的内嵌工作台操作：转写 → 复听修订 → 保存 TXT → MFA 对齐 → 编辑边界 → 保存人工版 → 导出 TextGrid。

在 iPad 上也可尝试用浏览器打开 notebook。若 iframe 下载不方便，使用第 9 步的下载单元；若触控拖动不方便，用开始／结束时间输入框修改边界。

这个文件不是公开部署的网站。每人运行自己的 Colab 会话；分享 notebook 不会共享同一个后台。音频会进入你选择的 Google 运行环境／Drive，程序包本身不含本地研究数据。免费托管运行时限制主要通过独立 Web UI 使用，本版本不使用隧道或保活绕过限制。

已验证：22 项本地测试、notebook 全部代码单元语法、内置源码与前端打包、Linux MFA 启动命令、精确代理 Origin 检查、ZIP 路径与原文件保护、浏览器禁用存储时的内嵌视图。

尚未验证：在你的 Colab 账号中实际安装与端到端运行、分配到的 GPU/CUDA 组合、iPad Safari 触控和下载。首次请用一个受试者试运行；如失败，保留报错单元和日志再定位。

官方参考：[Colab FAQ](https://research.google.com/colaboratory/faq.html)、[Google 的端口内嵌接口](https://github.com/googlecolab/colabtools/blob/main/google/colab/output/_util.py)。
