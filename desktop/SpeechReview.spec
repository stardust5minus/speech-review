# Build from the project root: python -m PyInstaller desktop/SpeechReview.spec
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

root=Path(SPECPATH).parent
datas=[(str(root/'frontend'/'dist'),'frontend/dist'),(str(root/'install_mfa.py'),'.'),
       (str(root/'desktop'/'THIRD_PARTY_NOTICES.txt'),'.')]
binaries=[]
hiddenimports=['uvicorn.logging','uvicorn.loops.auto','uvicorn.protocols.http.h11_impl','uvicorn.protocols.websockets.auto','uvicorn.lifespan.on','multipart','python_multipart']
for package in ('faster_whisper','ctranslate2','av','tokenizers','huggingface_hub','pypinyin','praatio','certifi'):
    data,binary,hidden=collect_all(package)
    datas+=data;binaries+=binary;hiddenimports+=hidden
a=Analysis([str(root/'desktop'/'launcher.py')],pathex=[str(root)],binaries=binaries,datas=datas,
           hiddenimports=hiddenimports,excludes=['torch','tensorflow','matplotlib','pandas','IPython','pytest'],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,a.binaries,a.datas,[],name='SpeechReview-Windows-x64',debug=False,
        bootloader_ignore_signals=False,strip=False,upx=False,console=False)
