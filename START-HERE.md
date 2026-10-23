# Speech Review — folder edition for Windows

1. Extract the entire ZIP into a writable folder, such as Documents\SpeechReview. Do not run it inside the ZIP preview.
2. Install **Python 3.11 or 3.12, 64-bit** if it is not installed. Use the standard Windows installer with the Python launcher or Add Python to PATH enabled.
3. Double-click **run.bat**. First launch creates `.venv` and installs the required libraries. Internet access is needed; wait for it to finish.
4. The launcher opens the workspace in your browser. For alignment, click **Install MFA (first use)** in the launcher, wait for completion, then refresh the workspace.
5. Keep the launcher open during review. Save text and boundaries before closing it.

The folder contains the Python source, built frontend, dependencies list, and startup scripts. Node.js and VS Code are not required to use it. Whisper and Mandarin models download on first use. Models and the MFA environment can require substantial additional disk space.

This edition keeps `data`, `models`, `runtime`, and `logs` inside the extracted folder. Back up `data`; keep source recordings accessible at their imported paths. Upgrading the code must preserve these directories. No recordings, saved projects, models, or personal credentials are included in the ZIP.

The separate EXE is an **experimental / testing preview**. It bundles Python, uses `%LOCALAPPDATA%\SpeechReview` for storage, and still needs testing on other computers. The folder edition is provided separately for users who prefer the Python source and startup scripts.
