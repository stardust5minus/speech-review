# Colab 独立网址版

1. 在 Google Colab 上传 `SpeechReview_Colab_Public.ipynb`。
2. 选择 GPU 运行时，按顺序运行。首次安装和模型下载需要时间。
3. 第 3 步可启用 Google Drive 保存；否则结束前请导出结果。
4. 第 7 步上传录音 ZIP（WAV 与同名 TXT），或填写已挂载的 Drive 文件夹。
5. 第 8 步点击 **Public URL**，输入本次显示的 Username / Password。

打开后与本地工作台相同：Whisper → 复听和修改 → 保存 TXT → MFA → 对齐与边界编辑 → 保存或导出 TextGrid。

Local URL 只供 Colab 虚拟机内部使用；电脑或 iPad 应打开 Public URL。无需 Cloudflare 账号。网址及密码在重启启动单元后改变，停止会话后失效。拥有网址与密码的人可以访问、修改同一份项目。

保持 Colab 会话运行即可，不提供自动保活。请在有可用计算额度且允许此计算流程的环境使用。分享 notebook 前清除输出，避免分享密码和研究资料。

程序代码已打包进 notebook，不需要上传整个本地项目。已验证代码、打包内容及认证；尚未在实际 Colab 会话和 iPad 上验收。

[Cloudflare 临时隧道说明](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
