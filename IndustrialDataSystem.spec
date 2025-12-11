# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_all

block_cipher = None

# Collect all submodules and data for key packages
scipy_imports, scipy_binaries, scipy_datas = collect_all('scipy')
sklearn_imports, sklearn_binaries, sklearn_datas = collect_all('sklearn')
matplotlib_imports, matplotlib_binaries, matplotlib_datas = collect_all('matplotlib')

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
    'scipy.sparse',
    'scipy.sparse.csgraph',
    'scipy.sparse.linalg',
    'scipy.stats',
    'scipy.signal',
    'sklearn',
    'sklearn.preprocessing',
    'sklearn.ensemble',
    'sklearn.tree',
    'sklearn.utils',
    'sklearn.utils._cython_blas',
    'sklearn.neighbors.typedefs',
    'sklearn.neighbors.quad_tree',
    'sklearn.tree._utils',
]

# Add collected submodules
hiddenimports += collect_submodules('sqlite3')
hiddenimports += collect_submodules('industrial_data_system')
hiddenimports += scipy_imports
hiddenimports += sklearn_imports
hiddenimports += matplotlib_imports

# Collect all data files
datas = [
    ('.env', '.'),  # Configuration file
]
datas += scipy_datas
datas += sklearn_datas
datas += matplotlib_datas

# Collect binaries
binaries = []
binaries += scipy_binaries
binaries += sklearn_binaries
binaries += matplotlib_binaries

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
