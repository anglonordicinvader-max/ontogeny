# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs

mujoco_datas, mujoco_binaries, mujoco_hiddenimports = collect_all('mujoco')
glfw_binaries = collect_dynamic_libs('glfw', destdir='glfw')

a = Analysis(
    ['mujoco_simulation.py'],
    pathex=['.'],
    binaries=[*mujoco_binaries, *glfw_binaries],
    datas=mujoco_datas,
    hiddenimports=[
        'websockets',
        'glfw',
        'mujoco.rendering.classic.renderer',
        'mujoco.rendering.classic.gl_context',
        *mujoco_hiddenimports,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # The standalone renderer reads MuJoCo sensors directly. Importing the
    # crawler_agent package here pulls the complete training stack through its
    # package initializer and is neither needed nor desirable in this process.
    excludes=[
        'pytest', 'notebook', 'IPython', 'crawler_agent', 'torch', 'tensorflow',
        'transformers', 'datasets', 'pandas', 'scipy', 'sklearn', 'pyarrow',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ontogeny-mujoco',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
