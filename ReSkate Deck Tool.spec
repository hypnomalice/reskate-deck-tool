from pathlib import Path
from PyInstaller.utils.hooks import collect_dynamic_libs
import ispc_texcomp
import PySide6

root = Path(SPECPATH)
engine = root / 'engine'
data = [(str(root / 'assets'), 'assets')]
data.append((str(root / 'licenses'), 'licenses'))
data.append((str(root / 'THIRD_PARTY_NOTICES.md'), '.'))
for folder in (engine, engine / 'depth-template'):
    relative = folder.relative_to(root).as_posix()
    data.extend([(str(folder / 'template-data'), relative + '/template-data'),
                 (str(folder / 'template-manifest.json'), relative)])
a = Analysis([str(root / 'Lenticular Deck Creator.pyw')],
    pathex=[str(root), str(engine)], binaries=collect_dynamic_libs('onnxruntime'),
    datas=data, hiddenimports=['onnxruntime.capi.onnxruntime_pybind11_state'],
    excludes=['pandas', 'matplotlib', 'onnxruntime.transformers', 'onnxruntime.quantization'])

# Qt needs its matching C++ runtime; another image library can supply an older copy.
qt = Path(PySide6.__file__).parent
runtime_names = {'msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll',
                 'msvcp140_codecvt_ids.dll', 'vcruntime140.dll',
                 'vcruntime140_1.dll', 'concrt140.dll'}
a.binaries = [(dest, str(qt / Path(source).name), kind)
              if dest.lower() in runtime_names and (qt / Path(source).name).is_file()
              else (dest, source, kind) for dest, source, kind in a.binaries]
# Qt uses Windows' ICU API, not Poppler's incompatible DLL with the same name.
a.binaries = [(dest, source, kind) for dest, source, kind in a.binaries
              if not (dest.lower() in {'icuuc.dll','icudt78.dll'} and 'poppler' in source.lower())]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas,
    name='ReSkate Deck Tool - Beta', console=False,
    icon=str(root / 'assets/app-icon.ico'))
