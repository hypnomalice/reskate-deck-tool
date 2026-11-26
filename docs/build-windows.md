# Build Deck Tool 1.11.0 on Windows

Use x64 Python, Visual Studio 2022 Build Tools with C++, CMake and the pinned dependencies in requirements-build.txt. Run from the source root in an x64 Visual Studio developer prompt:

```bat
python -m pip install -r requirements-build.txt
cmake -S native -B build/native -A x64
cmake --build build/native --config Release --parallel
pyinstaller --noconfirm "ReSkate Deck Tool.spec"
```

CMake builds both jiggle_preview.dll and shaker_preview.dll into their assets folders. The source archive includes the exact Luau VM/compiler source snapshot used by the shaker helper, with its MIT licence and source hashes. The C++ runtime is linked statically. No private SDK library is needed to build these helpers. Build products and Python caches are excluded from the source archive.

The app includes preview libraries, but does not include SDEC or the external Studio compiler. Native deck ZIP/direct export requires a separately installed shader-capable reskate_cli.exe supporting `--board-loader-from-core` and a local game installation.

Run authoring tests with `python -m unittest discover -s tests`. Optional SDEC_MATERIAL_CHECKER and RESKATE_LUAU_RUNNER paths enable native declaration and cross-language checks. These are developer test dependencies, not requirements for running the Windows app.

The executable supports `--self-test-shaker <new-output-folder>`. Without compile-config.json it tests project save/reload, size/weight/rim controls, grip preference and the moving preview. To also test first-run export setup and real ZIP export, put this file in that fresh output folder:

```json
{"game_root":"C:/Games/ReSkate","compiler":"C:/Tools/Studio/reskate_cli.exe"}
```

The check uses isolated settings and leaves normal user preferences alone. It selects the supplied paths through the actual first-run setup, verifies persistence, and exports grip-on/grip-off shaker decks through the real app export action. Use a fresh output folder each time; do not put an .export.json sidecar beside the tested executable.

Older native/build_jiggle_preview.cmd and native/build_shaker_preview.cmd entry points remain available for developers with an existing Luau library. The CMake build above is the standalone source-build route. Luau's upstream build targets are documented in its [CMake configuration](https://github.com/luau-lang/luau/blob/master/CMakeLists.txt); this archive includes only the VM/compiler dependencies needed here.

## Optional shader maintenance

The shipped runtime resource catalogue is ready for normal authoring and app builds. Rebuilding the per-layer holographic shader payloads is a separate maintainer task, not a requirement for deck authors or recipients. With Windows DXC tools, run `runtime-source/layer-holographic/build.py --dxc <DXC folder> --assembler runtime-source/layer-holographic/assemble_dxil.py --output <new packet folder>`. The preserved inputs are in baseline.zip. Native SDEC packaging must retain existing resource IDs, bundle placements and unrelated payloads.
