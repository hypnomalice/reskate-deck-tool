from pathlib import Path
from PyInstaller.utils.hooks import collect_dynamic_libs

root = Path(SPECPATH)
engine = root / 'engine'
data = [(str(root / 'assets'), 'assets')]
for folder in (engine, engine / 'depth-template'):
    relative = folder.relative_to(root).as_posix()
    data.extend([(str(folder / 'template-data'), relative + '/template-data'),
                 (str(folder / 'template-manifest.json'), relative)])
a = Analysis([str(root / 'Lenticular Deck Creator.pyw')],
    pathex=[str(root), str(engine)], binaries=collect_dynamic_libs('onnxruntime'),
    datas=data, hiddenimports=['onnxruntime.capi.onnxruntime_pybind11_state'],
    excludes=['pandas', 'matplotlib', 'onnxruntime.transformers', 'onnxruntime.quantization'])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas,
    name='ReSkate Deck Tool - Beta', console=False,
    icon=str(root / 'assets/sofi-deck-tool.ico'))
