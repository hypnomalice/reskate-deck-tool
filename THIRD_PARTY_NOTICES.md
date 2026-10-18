# Third-party components and assets

The MIT licence in this repository covers app-owned source. It does not relicense
third-party dependencies, the supplied character icon, or game-derived template data.

- `engine/template-data` and `engine/depth-template` contain the binary templates and
  compiled programs needed to construct the mods. Game-derived material remains subject
  to its original rights; no ownership or MIT licence to game assets is claimed.
- `assets/sofi-deck-tool.*` is the user-supplied character icon, not MIT-licensed artwork.
- ISPCTextureCompressor Python bindings: Rudolf Kolbe, MIT; native compressor components
  retain their upstream licences.
- Python, Tcl/Tk, Pillow, NumPy, ONNX Runtime, FlatBuffers and Protobuf retain their own
  licences. The `licenses` folder carries licence texts collected from the build environment.
- PyInstaller is a build dependency with its own bootloader exception.
- Optional depth model: Depth Anything V2 Small, Apache 2.0. It is not included in the
  executable. The pinned ONNX conversion and checksum are recorded in `auto_depth.py`.

No example decks or personal artwork are included. Source projects and generated images
belong to their respective authors.
