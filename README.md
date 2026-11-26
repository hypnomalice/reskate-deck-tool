# ReSkate Deck Tool 1.11.0

Create and export effect decks for ReSkate. Install **SDEC 3.6.0 or newer** separately and keep one copy enabled first in your mod list. Deck exports contain artwork and settings; SDEC supplies the shared effects and motion controllers.

## Windows download

Extract the Windows ZIP and run **ReSkate Deck Tool.exe**. Python is not required. The download includes the native libraries used by the animated preview.

Choose **Mod ZIP**, **Install to game**, or **FBMOD** in Export as. On the first ZIP or direct installation, select your game folder and a shader-capable Studio **reskate_cli.exe** supporting `--board-loader-from-core`. Studio and its compiler are separate prerequisites; they are not bundled or downloaded by this tool. Older compilers are skipped during automatic selection. Change these paths later in **File > Export setup**.

Import a generated ZIP through the ReSkate launcher, or extract its single mod folder into Mods. Close the game and launcher before direct installation. The tool backs up intact exports before updating them and refuses to replace unrelated or edited files.

Download [SDEC from Thunderstore](https://thunderstore.io/c/reskate/p/IdolRiot/Sofis_Deck_Effect_Core/). If Thunderstore has not yet updated to 3.6.0, the matching [SDEC 3.6.0 ZIP is also attached to this release](https://github.com/hypnomalice/reskate-deck-tool/releases/download/v1.11.0/IdolRiot-Sofis_Deck_Effect_Core-3.6.0.zip). Update your existing core and keep one copy enabled. A deck recipient needs ReSkate, SDEC and the exported deck pack; they do not need Deck Tool or the compiler.

## Per-layer holographic parallax

Choose Normal or Holographic independently for the foreground, middle and background of a parallax deck. Each layer has its own 0–100% strength and area selection: Light artwork, Whole layer or Mask PNG. White mask areas receive foil, black stays normal and grey gives partial coverage. Masks follow their layer’s artwork placement.

A normal front graphic can sit over a holographic background, or a holographic middle layer can move between two normal layers. The finish uses the donor Pearl pattern and view-dependent response. The preview uses approximate lighting; inspect the exported deck in game.

The older whole-board holographic overlay remains available for existing projects. Selecting a per-layer finish in the editor clears that overlay. Projects without per-layer settings retain their existing appearance. This feature requires SDEC 3.6.0 or newer; see [the layer finish guide](docs/per-layer-holographic.md).

## Shaker in Glass

Use a background image and one to three independent PNG pieces. Each piece has its own width, weight multiplier and collision shape: PNG outline, rectangle or circle. Pieces slide, spin and collide on one shallow plane. Separate depth planes are not supported.

Shaker decks require Mod ZIP or Install to game export; bare FBMOD export is not supported for this effect.

Clear acrylic rims are optional, with per-piece width from 0-5 mm and strength from 0-100%. Rim width contributes to the collision outline; strength changes appearance. Internal background blur defaults to zero. **Use equipped grip tape** is optional and preserves the user's selected grip design and stock alignment.

The moving preview runs the same Luau solver as SDEC. **Shake preview** applies container acceleration; **Pause**, **Dim background** and **Reset pieces** help inspect the effect. These inspection controls do not change saved deck settings. Lighting, reflections and the preview deck shape are approximate.

## Other effects

Animated/GIF, lenticular, depth map, parallax, Ghost Rare, metallic flakes, ink flow, impossible window, liquid bottle, neon, CD hologram, E-ink, holographic glitch, glass, clear case, crystal and artwork springs remain available. Finish options include surface sheen and holographic coating.

## Projects and compatibility

Save a project to retain image paths, placement and effect settings. Re-export to apply newly authored settings. Existing shaker projects without a grip preference retain grip enabled; an explicit off setting stays off. Existing clear-case exports receive the SDEC hole correction without re-exporting.

The release was checked on Windows x64 with the current ReSkate Dev installation. Cross-platform behavior and general multiplayer visibility have not been established. FitCheck capture of transparent decks is a known limitation. The preview is a guide; inspect your deck in-game before sharing it.

See [usage instructions](docs/USAGE.md), [1.11.0 release notes](docs/release-1.11.0.md), and [Windows source build instructions](docs/build-windows.md). Licences and third-party notices accompany the download. Older release notes are retained in docs for historical reference.
