# Mesh registration helper

`mesh-register.cpp` registers the cloned geometry and appearance routes used by e-ink and glitch exports. The Windows helper is shipped at `assets/mesh-register.exe`; no development checkout is needed to export decks.

To rebuild, use the ReSkate Studio source checkout and an x64 Visual Studio C++ developer command prompt:

```bat
cl /std:c++20 /EHsc /MT /O2 /I PATH_TO_STUDIO\src tools\mesh-register.cpp PATH_TO_STUDIO\src\modding\cosmetics\bundle_ref_table.cpp /Fe:assets\mesh-register.exe
```
