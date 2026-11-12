# Build the Windows app

Use Python with requirements.txt and PyInstaller. Build the native preview helper first, from an x64 Visual Studio 2022 developer prompt:

```bat
native\build_jiggle_preview.cmd
pyinstaller --noconfirm "ReSkate Deck Tool.spec"
```

The helper uses only the Windows/C++ standard runtime, statically linked. Its C++ source is native/jiggle_preview.cpp. Python source runs can fall back to NumPy when the DLL is absent; the packaged Windows build requires it for preview performance. Build products stay out of Git.

Run targeted tests with `python -m unittest discover -s tests -p "test_jiggle*.py"` and the Crystal tests. Optional SDEC_MATERIAL_CHECKER and RESKATE_LUAU_RUNNER paths enable checks against the runtime declaration parser and Luau solver. They are developer tools, not end-user dependencies.

The built app supports `--self-test-digital <output-folder>`. A compile-config.json in that folder, with game_root and compiler paths, also checks native installable export. No game or private Studio binaries are included in this repository or in the Windows download.

The authored pixel-warp and donor-surface isolation logic is in native/jiggle_shader.py. It rejects shader outputs that depend on texture bindings other than the authored atlas. Runtime payloads selected by assets/effects-runtime/manifest.json carry SHA-256 integrity checks.
