# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['main_ui.py', 'main_window_ui.py', 'network.py', 'networkprimitive.py', 'simulator.py', 'vehicle.py',
    'vehiclestrategy.py', 'dispatcher.py', 'dispatchstrategy.py', 'fleet.py', 'graph_generator.py', 'logger.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz_a = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

windowed_exe = EXE(
    pyz_a,
    a.scripts,
    [],
    exclude_binaries=True,
    name='transport_simulator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

b = Analysis(
    ['main.py', 'network.py', 'networkprimitive.py', 'simulator.py', 'vehicle.py',
    'vehiclestrategy.py', 'dispatcher.py', 'dispatchstrategy.py', 'fleet.py', 'graph_generator.py', 'logger.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz_b = PYZ(b.pure, b.zipped_data, cipher=block_cipher)

console_exe = EXE(
    pyz_b,
    b.scripts,
    [],
    exclude_binaries=True,
    name='transport_simulator_cmd',
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

c = Analysis(
    ['network_visualizer.py', 'network.py', 'networkprimitive.py', 'vehicle.py', 'fleet.py', 'logger.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz_c = PYZ(c.pure, c.zipped_data, cipher=block_cipher)

visualizer_exe = EXE(
    pyz_c,
    c.scripts,
    [],
    exclude_binaries=True,
    name='visualizer',
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

coll = COLLECT(
    windowed_exe,
    console_exe,
    visualizer_exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='transport_simulator',
)
