# -*- mode: python ; coding: utf-8 -*-
import sys 
from PyInstaller.utils.hooks import collect_all
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import copy_metadata

sys.setrecursionlimit(sys.getrecursionlimit() * 50)
datas = [("C:\\Users\\Me\\miniconda3\\envs\\venv\\Lib\\site-packages\\streamlit\\runtime", ".\\streamlit\\runtime"), ("C:\\Users\\Me\\miniconda3\\envs\\venv\\Lib\\site-packages\\streamlit\\static",".\\streamlit\\static"), ('utils', 'utils'), ('C:\\Users\\Me\\miniconda3\\envs\\venv\\Library\\bin\\tesseract.exe', '.\\tesseract\\'), ('C:\\Users\\Me\\miniconda3\\envs\\venv\\share\\tessdata', '.\\tessdata\\')]
datas += collect_data_files("streamlit")
datas += copy_metadata("streamlit")
datas += collect_data_files("timm")
datas += copy_metadata("timm")
datas += collect_data_files("tesseract", include_py_files=True)
binaries = []
hiddenimports = ['chromadb', 'chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2', 'chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction', "opencv-contrib-python", "cv2", "cv2.cv2","docx2pdf", "ggml-metal.metal", "llama_cpp", "timm", "clipboard", "numpy", "numpy.core.multiarray"]
tmp_ret = collect_all('langchain')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('scipy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('opencv-contrib-python')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('cv2')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('streamlit')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('chromadb')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('timm')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('transformers')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('tesseract')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('clipboard')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

a = Analysis(
    ['ACUNAO-AI.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['./hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ACUNAO-AI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ACUNAO-AI',
)
