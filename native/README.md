# Tool-only depth rasterizer

This small optional library implements depth_views._reference_view exactly, with the same depth ordering, 0.001 visibility tolerance, ties-to-even rounding, smooth-surface interpolation and far-boundary hole fill. It does not load into the game. Python remains the fallback if the library is unavailable.

Build in an x64 MSVC Developer PowerShell from the repository root:

    cl /nologo /LD /MT /O2 /fp:strict /W4 /WX /std:c++20 /EHsc native/depth_raster.cpp /Fe:assets/depth-raster.dll

Use a scratch directory for intermediate .obj/.lib/.exp outputs. Static CRT linking avoids a new runtime dependency. Do not use fast floating-point or fused multiply-add options: exact parity is intentional. The export and preview call the same full-resolution renderer; the existing atlas downsample and BC7 encoding remain unchanged.

Run tests/test_depth_parity.py against the original Python renderer before replacing the library. It covers discontinuities, overlap, flat/graded depth, one-pixel images, extreme strengths, both directions and fallback operation. No source artwork, shader payload or game DLL is changed by this backend.
