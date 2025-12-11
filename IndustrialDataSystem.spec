# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Build comprehensive hidden imports list
hiddenimports = [
    # Environment and configuration
    'dotenv',

    # Database
    'sqlite3',

    # Data file formats
    'nptdms',
    'openpyxl',
    'chardet',
    'pyarrow',
    'pyarrow.parquet',

    # Data processing
    'pandas',
    'numpy',

    # GUI and visualization
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'matplotlib.backends.backend_qt5agg',
    'mplcursors',

    # Machine learning and scientific computing
    'joblib',
    'scipy',
    'scipy.special',
    'scipy.special._ufuncs_cxx',
    'scipy.linalg',
    'scipy.linalg.cython_blas',
    'scipy.linalg.cython_lapack',
    'scipy.sparse',
    'scipy.sparse.csgraph',
    'scipy.sparse.linalg',
    'scipy.stats',
    'scipy.signal',
    'scipy.integrate',
    'scipy.optimize',
    'sklearn',
    'sklearn.preprocessing',
    'sklearn.ensemble',
    'sklearn.tree',
    'sklearn.utils',
    'sklearn.utils._cython_blas',
    'sklearn.neighbors',
    'sklearn.neighbors.typedefs',
    'sklearn.neighbors.quad_tree',
    'sklearn.tree._utils',
]

# Safely collect submodules
try:
    hiddenimports.extend(collect_submodules('sqlite3'))
except Exception:
    pass

try:
    hiddenimports.extend(collect_submodules('industrial_data_system'))
except Exception:
    pass

# Collect matplotlib data files
datas = []
try:
    matplotlib_datas = collect_data_files('matplotlib', include_py_files=True)
    datas.extend(matplotlib_datas)
except Exception:
    pass

try:
    scipy_datas = collect_data_files('scipy')
    datas.extend(scipy_datas)
except Exception:
    pass

# Add .env if it exists
datas.append(('.env', '.'))

# Modules to exclude
excludes = [
    'torch',
    'tensorflow',
    'PIL.ImageTk',
    'tkinter',
    'matplotlib.tests',
    'scipy.weave',
    'scipy._lib.array_api_compat.torch',
    'sklearn.externals.array_api_compat.torch',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='IndustrialDataSystem',
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
)
