# Speech Review on Google Colab

1. Download `SpeechReview_Colab_Public.ipynb` from this repository and upload it through Colab's **File > Upload notebook**. This works with a private GitHub repository without granting Colab GitHub access.
2. Run the cells in order. Installation logs are printed if a step fails. The public notebook uses an isolated Python environment and attempts to repair missing venv/pip support.
3. Optionally enable `PERSIST_TO_DRIVE` and authorize Drive to keep inputs and reviews across runtimes. Without Drive, export results before disconnecting.
4. Let MFA install for forced alignment; models download on the first alignment. A failed MFA installation does not prevent transcription review.
5. Start the service and open the **Public URL** in Step 8. Use the displayed username and password. The local URL is internal to the Colab virtual machine.
6. Import recordings in the notebook, or upload existing WAV/TXT/TextGrid sets from the alignment workspace. Review text, save, align, edit boundaries, and export.

The page starts in English. The header's English/中文 selector remembers your choice without reloading or dropping unsaved edits. Research text and filenames are never translated.

The public URL is temporary and requires the runtime to remain active. Save reviewed boundaries and download results before stopping. Notebook outputs can contain access credentials or research material; clear outputs before sharing.

To update an existing Colab copy, upload the latest notebook or replace its setup cells with the latest version, then rerun setup. GitHub updates do not change existing Drive notebook copies. Local project data is not embedded in the notebook.
