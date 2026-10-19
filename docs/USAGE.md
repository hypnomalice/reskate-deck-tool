# ReSkate Deck Tool - Beta

Make custom lenticular skateboard graphics for ReSkate. Export one deck or a workspace
of decks as an `.fbmod`, with custom names and thumbnails.

Animated GIF mode also accepts animated PNG and WebP. It loops the clip on the
underside, centred without stretching. Placement controls adjust its position and
scale; the preview plays while you edit. Export animated and lenticular decks in
one pack or as separate compatible mods.

This beta supports up to 512 frames and 40.95 seconds. Clips up to 4.095 seconds
use millisecond timing; longer clips use 10-millisecond timing. The source frame
durations are preserved within that precision; a higher quality setting does not
invent extra frames.

Choose Standard, High or Ultra for increasing frame detail and file size. Frames
share one game texture, so longer clips still have less room per frame. GIF exports
include a shared compositor fix to preserve atlas detail, using native compression
without extra compositor mip levels to reduce texture memory. This changes the
shared board compositor while the mod is enabled; memory use still depends on the
game and enabled mods. Whole-game memory savings have not been benchmarked.

Older lenticular exports must be re-exported
with this version, or have their shared renderer upgraded, before combining them
with animated mods. Do not enable an old pack and its replacement together.

## Update existing packs

Choose **File > Update existing FBMODs...**, select one or more older Deck Tool
packs, then choose a folder for the updated copies. No project or source images
are needed. Originals remain unchanged; existing output files are never replaced.
The updater recognises published Deck Tool renderers and skips unsupported files
with an explanation.

Import the new `- Compatible.fbmod` files in shader-capable ReSkate Studio and
replace their older versions in the enabled mod list. Update every older effect
pack you use together. New exports already include the sticker fix.

## Preview and updates

The board stays full-height in the centre, with separately scrolling image settings
on the left and lens/effect/placement controls on the right. Position controls redraw
while dragging; the complete effect refreshes after release. The previous preview
stays visible during background updates, and GIF playback keeps its position.

The effect preview samples the exported atlas layout in linear colour, matching the
shader's flip direction, depth-view blending, lens-strength decoding and layer alpha.
Depth views prepare in the background; angle changes reuse the prepared texture.
This is an effect preview, not a copy of the game's renderer: lighting, reflections,
texture compression, camera geometry and the truck guides remain approximate.

On startup the app checks this repository's GitHub releases in the background.
An **Update available** button appears only for a newer release. It opens that release
on GitHub; it does not replace the executable or install anything automatically.
Beta builds also check beta releases. Offline and rate-limited checks stay quiet.

Stickers now composite separately from effect artwork. Dark artwork in gameplay remains a known issue.

## Download and run

Download the Windows ZIP from [Releases](https://github.com/hypnomalice/reskate-deck-tool/releases),
extract it, and open **ReSkate Deck Tool - Beta.exe**. Python and the required libraries
are bundled. Windows is the tested platform; a clean-machine test is still pending.

**You need a ReSkate Studio build with shader support to import and deploy the mods.**
The tool exports files; it does not install or enable them.

## Make a deck

1. Set the deck name and choose an effect.
2. Choose your images. Matching 512 × 2048 canvases are a good starting point.
3. Adjust sizing and placement using the live preview.
4. Choose a thumbnail or keep the automatic one.
5. Save your workspace so you can edit it later. Keep its source images in place.
6. **Export .fbmod** exports the selected deck; **Export all** combines the workspace.
7. Import the file in shader-capable ReSkate Studio and test it in game.

The in-app Guide and question-mark tooltips explain the controls. The preview is
approximate: lighting, deck curvature and gameplay can change the result.

### Effects

- **Lenticular:** two graphics flip as the viewing angle changes.
- **3D (depth map):** one colour image and an aligned grayscale map; white is near,
  black is far. Begin with low depth strength and check for stretched edges.
- **3D (foreground/background):** a transparent foreground over a complete background.
  Background motion splits movement between the planes; lens texture controls banding.

Auto depth generation is optional and uses an AI estimate. Its dialog offers:

- **Light (Small)** — the default, 99.1 MB, Apache 2.0.
- **Full (Base)** — 388.9 MB, CC BY-NC 4.0, **non-commercial use only**.

Each model downloads only when requested and is cached separately. Full uses more
memory and can take longer; it is not guaranteed to improve every image. Generation
runs locally; artwork is not uploaded. A carefully made depth map can be more accurate.
Model homepages: [Small](https://huggingface.co/depth-anything/Depth-Anything-V2-Small),
[Base](https://huggingface.co/depth-anything/Depth-Anything-V2-Base).

## Current limits

- Use distinct deck names, including across separately exported mods: identities derive from names.
- Multiple decks and separate mods have been tested, but no unlimited collection size is guaranteed.
- Foreground/background mode can show sectional movement in gameplay.
- Custom wood tint exports a private wood texture for each tinted deck. Choose
  a colour and adjust Wood intensity from 0–200%; Original wood retains the game's
  natural texture. Edge colours have been checked in the board menu; gameplay and
  broken-board checks are still pending for this feature.
- Updates to the shared renderer across independently published mod versions need more testing.
- Projects reference image files rather than embedding them.

Board Break, classic flip, depth and multiple-deck exports have been tested on the
author's setup. Test your own artwork in the menu, gameplay and on a broken board.

## Run from source (Windows, Python 3.12)

The Cutroom interface uses Qt (PySide6 Essentials). The Windows EXE bundles it;
no separate Qt installation is needed. Deck tabs retain each deck's settings.
The numeric boxes and +/− buttons allow precise adjustment alongside the sliders.

Depth previews use a fast interactive approximation; exports retain the full
depth-buffer renderer. Lens detail compares 0% with the current setting using
an enlarged crop selected from a responsive area of the artwork. The lens slider
controls fine angle variation, not a striped overlay. It can be subtle with low
parallax or flat artwork. Preview lighting and board curvature remain approximate.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe "Lenticular Deck Creator.pyw"
```

## Build the executable

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.venv\Scripts\python.exe -m PyInstaller --noconfirm "ReSkate Deck Tool.spec"
```

The executable appears in `dist/`. It includes the runtime and required template data;
the optional depth model is downloaded separately.

To run the packaged export check, launch the EXE with `--self-test` and an output folder.
It creates a classic/depth/GIF test pack with coloured wood and `build-check.json` with the result. This checks
archive structure, resource references and dependencies, not game compatibility.

## Licence and credits

App-owned source code is MIT licensed. See [LICENSE](../LICENSE) and
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) for dependencies and non-code assets.
This is an unofficial community tool, not affiliated with the game publisher.

