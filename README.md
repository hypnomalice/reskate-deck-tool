# ReSkate Deck Tool 1.7.0

Create effect decks and export them as installable mod ZIPs, directly to your game, or as FBMODs.

- **Artwork Springs:** use artwork, an optional depth map and a white-on-black jiggle mask. Tune amount, stiffness, depth, top/both attachments and fixed points. The close-up and **Tilt and release** test help judge movement and settling. Settings are saved in the deck; SDEC runs the shared controller.
- **Crystal:** tune tint, cut density and optional equipped grip tape.
- Faster spring previews use the same spring equations and inverse texture warp as the native effect. Delayed rendering no longer resets the springs. Lighting and deck geometry remain approximate.
- Native exports retain the shared-core loader path and private material registrations. Artwork Springs uses its authored atlas without donor surface patterns.

**Crystal and Artwork Springs require SDEC 3.1.0 or newer**, installed separately and enabled first in the mod list. Keep only one core enabled. Native preview jiggle requires **ReSkate 2.1.4-5 Hotfix or newer**, containing [PR #467](https://github.com/Dingo-Shenanigans/ReSkate/pull/467). No custom DLL is needed on that release.

For ZIP/direct exports, select a shader-capable Studio command-line compiler in File > Export setup. It must support `--board-loader-from-core`; the compiler is not bundled or downloaded.

See [1.7.0 controls and release notes](docs/release-1.7.0.md) and [source build instructions](docs/build-windows.md).

## 1.6.6 — previous release

Create Clear Case, E-ink, Glitch, Animated / GIF, Lenticular (2â€“8 pictures), Depth Map, Parallax (2â€“3 images), Ghost Rare, CD Hologram, Metallic Flakes, Ink Flow, Impossible Window, Liquid Bottle and Neon decks.

Requires **SDEC 2.1.5**, enabled at **number 1** in the mod list. Keep one core enabled.

- E-ink retains the accepted reference flash and switches the fixed page at full flash in either tilt direction. Refresh tilt range controls angular width. No timed controller or custom ReSkate DLL is required.
- Clear Case places artwork inside a layered shell, with frosted/glossy finishes, working tint, blur and depth controls. Default internal blur is 42%.
- Separate full-canvas masks place decorative case screws and moulded details on the underside. White screw-mask spots create up to 16 screw bosses; white/grey detail-mask areas add plastic detail. Black removes the defaults. Reset restores them. The upper/grip side keeps fixed truck holes. Grip tape defaults off.
- Repairs native material registration for clear-case and glitch exports, preserving their material routes when combined with SDEC.
- Preserves RGB, single-colour and two-colour glitch options, optional white sheen, and opt-in holographic depth/parallax.

Use a shader-capable Studio compiler supporting core board-loader inheritance for direct Clear Case/Glitch exports. Set your game folder and compiler in File > Export setup. The compiler and SDEC are installed separately.

Re-export existing projects to use the updated effects. The shared core also preserves the original unmarked e-ink reference behavior. Development effects remain in progress.

## 1.6.2 - export repair and shell finishes

Requires **SDEC 2.1.4**, at **number 1** in the mod list. Glitch exports include their registration helper. Clear Case offers frosted/glossy plastic, tint, haze and internal movement. Glitch supports RGB, one-colour and two-colour palettes. Parallax and Depth Map have an explicit optional holographic overlay, off by default.

## 1.6.1 - preview repair

Fixes artwork preview loading and adds clock-driven glitch preview animation. Clear Case authoring was added in 1.6.2.

## 1.6.0 - e-ink and lenticular plastic

E-ink converts both pages to a four-tone paper palette and refreshes with board tilt. Refresh tilt range controls how much rotation the flash takes; it is not a timer or persistent display memory. The approved ridged plastic finish is enabled by default for two-image lenticular decks, with an on/off switch and strength control. Requires **SDEC 2.1.3 or newer**, placed **number 1** in the mod list.

## 1.5.1 â€” centred CD artwork depth

CD depth movement now uses the accepted centred relief response. The preview follows that response, original depth gradients are preserved, and optional scratch visibility is improved. CD depth changes require **SDEC 2.1.1 or newer**. **SDEC must be number 1 in your mod list.** Depth-driven holographic relief remains experimental and is not enabled by normal exports. See [1.5.1 release notes](docs/release-1.5.1.md).

## Editor workflow

The dark editor keeps the deck list and main effect selector on the left, the preview and viewing-angle slider in the centre, and Artwork / Effect / Finish tabs on the right. Artwork supports size, position, rotation and optional linked layer transforms. Plain wheel scrolling does not alter settings. Ctrl + wheel zooms artwork; Ctrl + Shift + wheel rotates it. See [1.5.0 release notes](docs/release-1.5.0.md).

## Direct installable export

The visible Export as selector offers Mod ZIP, Install to game, and FBMOD. The export buttons follow the selected option, which is remembered between sessions. ZIP export runs a selected shader-capable Studio command-line compiler in the background; the editor never opens and no manual FBMOD import/deploy is needed. It still requires that compiler to be installed. The compiler is not bundled or downloaded.

Choose the game folder and compiler once; File > Export setup changes them later. ZIP export does not install or enable anything. Install to game asks for a folder name every time, then writes the deck pack straight into the selected gameâ€™s Mods folder; close the game and launcher first, then enable the mod in the launcher. Updates back up unchanged Deck Tool exports and refuse to replace unrelated or externally edited files. Import it through the ReSkate launcher, or extract its mod folder into Mods. Compilation and packaging are staged, and a failed build preserves the previous exported ZIP. SDEC remains a separate Thunderstore install.

## SDEC required

Effect decks require [SDEC: Sofis Deck Effect Core](https://thunderstore.io/c/reskate/p/IdolRiot/Sofis_Deck_Effect_Core/). Enable one current copy alongside your artwork packs. New tool exports contain the deck content only.

Use SDEC 1.2.0 or newer for Neon and multi-picture lenticular. Install the core separately from Thunderstore; the tool does not download it. No custom game DLL is required.

## Depth preview accuracy

Depth Map previews now share the full-resolution export renderer, including overlap and hole filling. Smooth Depth and Ghost Rare use the native shader displacement sequence, and their 3D previews use the calibrated camera response. An optional tool-only native helper accelerates depth rendering while preserving the Python reference pixels; the Python renderer remains the fallback. See [1.4.7 release notes](docs/release-1.4.7.md).

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

- Lenticular: choose 2â€“8 pictures. Move pictures up/down to set their viewing order. Original lens-strip transitions are retained; old two-image projects still open.

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

## 1.5.0 â€” CD hologram and finishes

See [CD Hologram controls](docs/cd-hologram.md). CD exports and optional white sheen require SDEC 2.1.0+. Update the existing core through Thunderstore; keep only one core enabled. No replacement game DLL is included.


Artwork Springs supports **Mod ZIP** and **Install to game** exports, which include the authored movement settings. Bare FBMOD export remains available for the other effects.
