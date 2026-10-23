# Speech Review

Whisper transcription, audio review, Montreal Forced Aligner (MFA) alignment, and editable Praat TextGrid boundaries in one workspace.

## Interface language

Choose **English** or **中文** in the page header. The preference is remembered on the current browser and origin. Switching languages does not reload the project or discard unsaved edits. Transcripts, interval labels, notes, and filenames stay in their original language.

## Run locally

Use Python 3.11 or 3.12. The built frontend is included; Node.js is needed only to rebuild it.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8765
```

Open http://127.0.0.1:8765/?lang=en in your browser. Stop the server with Ctrl+C. After installing dependencies, Windows users can also run `powershell -ExecutionPolicy Bypass -File .\start.ps1`. Open this folder in VS Code to use the included launch configuration.

## Transcription and review

1. Import a local folder containing WAV recordings and optional matching TXT files. Original TXT files are references; they are not required. Local folder import reads files directly in that folder.
2. Select a task condition or let the app detect number, homo, or nonhomo from filenames.
3. Run Whisper for all remaining recordings or an individual trial. Models download on first use. The original notebook profiles prefer GPU medium for Number/Homo and GPU large-v3 for Non-homo, with CPU medium/int8 fallback.
4. Review the raw transcript, listen, edit the review text, and save. The original script's replacement and deduplication result is shown separately for optional adoption. Raw transcription is retained.
5. Save all TXT files and export the saved results. Exported TXT names match the original filenames, or the audio stem when no original TXT exists. Tags and notes are stored separately from the transcript.

Saved human text and tags survive rerunning Whisper. Source recordings and original TXT files are read only.

## Alignment and boundary editing

Install the isolated MFA environment:

```powershell
.\.venv\Scripts\python.exe install_mfa.py
```

MFA 3.3.10 uses `mandarin_mfa` and `mandarin_china_mfa`; models download on the first alignment. Save corrected transcripts before running batch alignment. Automatic and manually reviewed boundaries are stored separately. Changing the transcript makes incompatible old alignments stale.

In **Alignment and boundary editing**, select a recording, drag boundaries, enter precise times, or edit interval labels. Click a word or the waveform between boundaries to play that interval. Drag across the waveform to play an arbitrary selection. Use the overview, time ruler, and zoom controls to navigate.

Keyboard controls while the editor is active:

- Space: play the selected range or interval.
- Enter: insert a boundary at the time cursor; text can split at the input caret.
- Alt+Backspace: remove the selected boundary and merge adjacent labels.
- Ctrl+Z: undo boundary edits.
- Ctrl+S: save reviewed boundaries.

Save reviewed boundaries before exporting. **Export reviewed TextGrids** includes only human versions and uses the audio stem, for example `3nonhomo_069_trial9.TextGrid`. The complete export keeps automatic and reviewed versions distinct. TextGrids contain actual alignment intervals, including empty intervals.

## Import existing WAV, TXT, and TextGrid files

The alignment workspace supports batch file or folder upload. Match files by stem; accepted TextGrid names include `stem.TextGrid`, `stem_reviewed.TextGrid`, and `stem_auto.TextGrid`, in that preference order. A words/word tier or a single interval tier is supported. All files are validated before a new project is created.

Imported TextGrids are ready for manual review without rerunning Whisper or MFA. Interval labels provide the reviewed transcript; the original TXT remains available as a reference. Uploaded copies are stored under `data/inputs/`.

## Annotation export for Google Sheets

In the transcription workspace, select **Self correction**, **Silence**, **Disfluency**, **Wrong word / pronunciation to check**, or **Other** and enter details in the notes. **Save and export Sheet annotations** saves the current tags, notes, and eligible transcript edits before downloading `annotations_sheet.csv`.

The CSV has `participant` and `annotation` columns: one participant per row, with multiple annotation lines inside a cell. Example: `001 - trial11 - filler - disfluency`. Multiple tags are combined, silence counts are summarized, and participant/trial IDs come from filenames. Only human-selected tags are exported. A matching TXT and preview are also available.

## Google Colab

[Open the shared Google Colab notebook](https://colab.research.google.com/drive/12JEJfQfNyENvVLifu2drSKOuZvG6l7FL?usp=sharing)

Upload **SpeechReview_Colab_Public.ipynb** to Colab and run its cells in order. Step 8 provides a temporary public URL and generated login credentials for the full interface, including on an iPad. The interface opens in English and can switch to Chinese. See [Colab instructions](COLAB.md).

The notebook embeds the application, so it does not need access to this private repository at runtime. Dependencies install in a separate Python environment. Optional Drive storage persists inputs, reviews, and boundaries; otherwise save and export before the runtime ends. The public URL expires when the runtime stops. Existing Drive notebook copies do not update automatically when this repository changes: upload the new notebook or replace its setup cells and rerun setup.

**SpeechReview_Colab.ipynb** is the alternate embedded-interface version; see [embedded notebook instructions](COLAB_EMBEDDED.md). Actual Colab execution depends on runtime resources and still needs verification in your account.

## Data and development

Project state, ASR history, reviews, tags, and boundary history are stored under `data/<project-id>/`; corrected text is in `corrected/`. Back up the entire data directory. Set `SPEECH_REVIEW_DATA` to choose another data directory. Source paths must remain accessible for locally imported recordings.

The original notebook constants and functions live in `backend/notebook_code/`; its manifest records the source hash. Recordings, transcripts, reviews, model weights, credentials, and local environments are excluded from this repository.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

To rebuild the frontend, install dependencies from `frontend/package.json` with pnpm, then run `pnpm build` from `frontend/`.
