# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for AI Assistant Python Backend
# Run from inside python_backend/ with:
#   pyinstaller backend.spec

import os
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_dynamic_libs

# Collect all files for complex packages
vosk_datas, vosk_binaries, vosk_hiddenimports = collect_all('vosk')
llama_datas, llama_binaries, llama_hiddenimports = collect_all('llama_cpp')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=vosk_binaries + llama_binaries,
    datas=[
        # Vosk model
        ('vosk-model-small-en-us-0.15', 'vosk-model-small-en-us-0.15'),
        # App source folders
        ('agents', 'agents'),
        ('plugins', 'plugins'),
        ('tools', 'tools'),
        ('locales', 'locales'),
    ] + vosk_datas + llama_datas,
    hiddenimports=[
        'uvicorn', 'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto',
        'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan', 'uvicorn.lifespan.on',
        'fastapi', 'fastapi.middleware', 'fastapi.responses', 'fastapi.staticfiles',
        'starlette', 'starlette.routing', 'starlette.middleware',
        'multipart', 'python_multipart',
        'vosk', 'wave', 'json', 'gtts',
        'pydantic', 'pydantic.v1',
        'fuzzywuzzy', 'Levenshtein',
        'psutil', 'dotenv',
        'duckduckgo_search',
    ] + vosk_hiddenimports + llama_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'PIL', 'cv2', 'torch'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='kruboo_backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,  # Keep console for debugging
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='kruboo_backend',
)
