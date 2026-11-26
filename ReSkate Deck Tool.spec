from pathlib import Path
import json
from PyInstaller.utils.hooks import collect_dynamic_libs
import ispc_texcomp
import PySide6

root = Path(SPECPATH)
engine = root / 'engine'
if not (root/'assets/jiggle-runtime/jiggle_preview.dll').is_file():
    raise SystemExit('Build native/build_jiggle_preview.cmd before packaging the Windows app.')
if not (root/'assets/shaker-runtime/shaker_preview.dll').is_file():
    raise SystemExit('Build native/build_shaker_preview.cmd before packaging the Windows app.')
data = [(str(root / 'assets'), 'assets')]
data.append((str(root / 'licenses'), 'licenses'))
data.append((str(root / 'THIRD_PARTY_NOTICES.md'), '.'))
for folder in (engine, engine / 'depth-template'):
    relative = folder.relative_to(root).as_posix()
    data.extend([(str(folder / 'template-data'), relative + '/template-data'),
                 (str(folder / 'template-manifest.json'), relative)])
a = Analysis([str(root / 'Lenticular Deck Creator.pyw')],
    pathex=[str(root), str(engine)], binaries=collect_dynamic_libs('onnxruntime')+collect_dynamic_libs('shapely'),
    datas=data, hiddenimports=['layer_finish_check','layer_finish','layer_finish_ui','transparency_check','transparency_preview','transparency_ui','transparency_native','transparency_vertex','transparency_finish','onnxruntime.capi.onnxruntime_pybind11_state','jiggle_ui','jiggle_effect','jiggle_physics','jiggle_native','jiggle_preview','jiggle_preview_ui','jiggle_layers','shaker_effect','shaker_native','shaker_preview','shaker_ui','shaker_check','shapely'],
    excludes=['gemstone_study','pandas', 'matplotlib', 'onnxruntime.transformers', 'onnxruntime.quantization'])

# Package only the selected runtime, not archived development shader payloads.
a.datas=[(dest,source,kind) for dest,source,kind in a.datas
         if not dest.replace('\\','/').startswith('assets/jiggle-runtime/')
         or Path(dest.replace('\\','/')).name != 'controller.lua']

# Keep only the dependency catalogue needed to separate deck content.
# The SDEC core and its resource payloads are distributed separately.
runtime_files={'manifest.json','base-dependencies.json'}
a.datas=[(dest,source,kind) for dest,source,kind in a.datas
         if not dest.replace('\\','/').startswith('assets/effects-runtime/')
         or Path(dest.replace('\\','/')).name in runtime_files]

a.datas=[row for row in a.datas if not row[0].replace('\\','/').startswith('assets/runtime-bundle/')]

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
    name='ReSkate Deck Tool', console=False,
    icon=str(root / 'assets/app-icon.ico'))
