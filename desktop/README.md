# Windows desktop build

`SpeechReview-Windows-x64.exe` is a portable Windows x64 application. No Python installation, administrator access, or VS Code is required. It opens the existing bilingual workspace in the default browser and keeps a small launcher window open.

1. Download and double-click the EXE.
2. Use **Open workspace** if the browser does not open automatically.
3. Import recordings, run Whisper, review, and save as usual. Whisper models download on first use. CPU mode is available; GPU use requires compatible NVIDIA libraries on the computer.
4. For forced alignment, click **Install MFA (first use)** in the launcher. Wait for completion and refresh the workspace. Mandarin models download during the first alignment.
5. Save text and reviewed boundaries before closing the launcher. Closing it stops the local service.

Files persist under `%LOCALAPPDATA%\SpeechReview`:

- `data`: project state, uploaded inputs, saved text, and reviewed boundaries. Back up this directory.
- `models`: downloaded Whisper and MFA models.
- `runtime`: the isolated MFA environment.
- `logs`: startup and MFA installation logs.

Replacing the EXE does not delete these directories. Projects from a source-code installation are not automatically migrated. Export/import WAV, TXT, and reviewed TextGrid sets to transfer work. Source-path imports still need the original recordings to remain accessible.

The application listens only on `127.0.0.1`, uses a free port, and reuses an existing instance when opened twice. No research materials or user credentials are bundled. First-time downloads require internet access. This preview has not been code-signed; Windows may identify it as an unrecognized application.

## Build from source

On Windows x64, from the project root:

```powershell
python -m pip install -r requirements.txt
python -m pip install pyinstaller==6.22.3
python -m PyInstaller --noconfirm desktop/SpeechReview.spec
```

The EXE is created in `dist/`. Rebuild `frontend/dist` before packaging frontend changes. The specification deliberately excludes project data, runtime environments, and model caches.

To test the actual EXE without opening a workspace:

```powershell
.\dist\SpeechReview-Windows-x64.exe --home C:\Temp\SpeechReview-Smoke --smoke-test
```

Check `smoke-test.json` and `logs/desktop.log` in the test home. Use an isolated directory; this flag does not touch the default user data directory.
