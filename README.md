# ReSkate Deck Tool 1.4.4

Create Animated / GIF, Lenticular (2–8 pictures), Depth Map, Parallax (2–3 images), Ghost Rare, Metallic Flakes, Ink Flow, Impossible Window, Liquid Bottle and Neon decks.

## SDEC required

Effect decks require [SDEC: Sofis Deck Effect Core](https://thunderstore.io/c/reskate/p/IdolRiot/Sofis_Deck_Effect_Core/). Enable one current copy alongside your artwork packs. New tool exports contain the deck content only.

Use SDEC 1.2.0 or newer for Neon and multi-picture lenticular. Install the core separately from Thunderstore; the tool does not download it. No custom game DLL is required.

## Calibrated deck previews

The 2D/3D preview now uses a measured standard-deck outline and artwork coverage, revised truck guides, and lighting calibrated against game-menu captures. Lenticular viewing direction and transitions are calibrated against 2/4/8-picture examples. Ink Flow and Impossible Window use the authored shader calculations; neon separates artwork from emission, and liquid fill follows board tilt and gravity. Optional exported-texture inspection shows compression results.

This is a calibrated approximation, not the game renderer: depth displacement, bloom, live liquid sloshing and lighting in other rooms/maps can differ. Export artwork and game shaders are unchanged. See [1.4.4 release notes](docs/release-1.4.4.md).

## Faster exports and responsive previews

Texture compression and large depth-view generation now run in parallel without changing their output. Bounded in-memory caches reuse unchanged work during repeat exports. Effect previews render off the UI thread, with lighter angle-drag frames and full resolution restored after release. See [1.4.3 release notes](docs/release-1.4.3.md) for measured timings and limits.

## Thumbnail correction

Automatic thumbnails now use the same visible-artwork mapping as the deck preview. This removes white source margins that appeared at the nose despite being outside the in-game artwork area. Custom thumbnails, project placement, shader strips and exported deck artwork are unchanged. Re-export existing packs to regenerate their thumbnails.

## New controls

- Preview placement now uses the standard deck's measured artwork UV coverage instead of stretching the complete image over the visible board. The shader header is already handled by the renderer; it is not applied twice. Existing image positions and exported artwork are unchanged.
- Switch the deck preview between **2D** and **3D**. Both use the same corrected artwork mapping. Drag the 3D view to orbit; double-click to reset. The enlarged preview follows the selected view.
- The 3D shape is a procedural standard-deck approximation. Other custom shapes and in-game lighting can differ. The preview switch adds no experimental effects or game DLL requirement. Ghost Rare area selection needs the updated core described below.

- Lenticular: choose 2–8 pictures. Move pictures up/down to set their viewing order. Original lens-strip transitions are retained; old two-image projects still open.
- Neon: load artwork and a glow mask PNG. White glows, black stays unlit, grey reduces glow. Transparent mask pixels stay unlit. Glow takes its colour from the artwork.
- Pick a colour: automatically selects matching artwork colours; tolerance controls how close they must be.
- Neon brightness: 100% matches the approved Neon C test. The preview is illustrative; in-game exposure and bloom vary.

All earlier effects, PNG transparency, placement, custom thumbnails, wood tint and project saving remain available. Examples/All Effects.json is a portable project with 15 test decks covering every effect and the main variants.

Private Studio source and game binaries are excluded.

## Ghost Rare finish areas

Silver and holo have independent area controls: **Whole board**, **Mask PNG**, or **Pick a colour**. For masks, white applies the finish, black keeps the original artwork, and grey/alpha softens the finish. Use a mask aligned with the full source artwork; it follows the artwork fit and placement. Colour selection uses the placed artwork and the tolerance slider. Outside both selected areas, the original colour artwork remains visible with the depth effect.

Existing projects keep whole-board finishes. Selected areas require SDEC core **1.3.0**, installed separately from Thunderstore. The tool does not download or bundle the core. Do not enable two copies of the core together. No custom game DLL is needed.

## Source

The source code is here, we had to use ai assistance to finally get the damn thing working, so any help removing the ai code and getting it fully human would be greatly appreciated
