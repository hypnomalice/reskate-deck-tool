# Third-party components and assets

The MIT licence in this repository covers app-owned source. It does not relicense
third-party dependencies, the supplied character icon, or game-derived template data.

- `engine/template-data` and `engine/depth-template` contain the binary templates and
  compiled programs needed to construct the mods. Game-derived material remains subject
  to its original rights; no ownership or MIT licence to game assets is claimed.
- `assets/sofi-deck-tool.*` is the user-supplied character icon, not MIT-licensed artwork.
- `assets/app-icon.*` is the user-supplied butterfly logo, not MIT-licensed artwork.
- `assets/board-compositor*.ebx` contains game-derived compositor templates and is
  subject to the same original rights as the engine templates.
- `assets/board-wood.*` contains the game-derived wood texture and texture-asset
  template, subject to the same original rights.
- ISPCTextureCompressor Python bindings: Rudolf Kolbe, MIT; native compressor components
  retain their upstream licences.
- Python, Tcl/Tk, Pillow, NumPy, ONNX Runtime, FlatBuffers and Protobuf retain their own
  licences. The `licenses` folder carries licence texts collected from the build environment.
- PyInstaller is a build dependency with its own bootloader exception.
- The Cutroom interface uses PySide6, Shiboken6 and Qt 6.12 under their upstream
  LGPL/GPL/commercial terms. The bundled build uses the LGPL distribution, with
  licence texts in `licenses/qt`. Qt libraries are loaded dynamically; the app's
  source and build instructions allow rebuilding with replacement libraries.
  Upstream sources: https://code.qt.io/cgit/pyside/pyside-setup.git/ and
  https://code.qt.io/cgit/qt/qtbase.git/ (6.12.0).
- Optional depth models: Depth Anything V2 Small (Light), Apache 2.0; Depth Anything
  V2 Base (Full), CC BY-NC 4.0, non-commercial use only. Neither is included in the
  executable. Pinned ONNX revisions and checksums are recorded in `auto_depth.py`.

No example decks or personal artwork are included. Source projects and generated images
belong to their respective authors.
