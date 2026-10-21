# ReSkate Deck Tool 1.1.0

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
share one game texture, so longer clips still have less room per frame.
The shared core preserves native compositor settings to avoid the clothing blur
observed with the previous resolution override.

## Shared core and existing packs

New exports save deck content plus `ReSkate Effects Runtime.fbmod`. Import the
runtime once, or install Sofi’s Deck Effect Core 1.0.1 through Thunderstore.
Keep one updated core enabled alongside your content packs.

For legacy standalone packs, use **File > Migrate older packs (once)…** and import
the new content copies in place of the originals. Original files stay unchanged.
Once migrated, existing content does not need re-exporting for this core update.
**File > Effects runtime setup…** saves the bundled core for import into Studio.

### Legacy repair history

The following notes apply to earlier standalone exports and their repair tools.
Use the migration flow above in version 1.1.0.

### Files exported or updated with beta.1 or beta.2

Use v0.1.5-beta.3 or newer to repair these packs. Beta.3 registers the compositor's
empty texture globally, so packs work without the Sticker Mask Probe development
mod. This has been checked in game with the probe disabled. Run affected FBMODs
through the updater, then re-import the repaired copies in Studio.

### Beta.1 resource-count issue

That release omitted the five metadata entries from the FBMOD resource count.
Studio could skip five resources even though their data was still in the file.
The current updater repairs these affected files directly.
After updating, re-import the repaired copies and replace the broken versions in
ReSkate Studio. Your artwork and settings do not need recreating.

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
An **Update available** button appears for a newer release. Packaged 1.1.0 builds
download and verify the EXE, preserve the previous executable and restart into
the update. Source runs and unverifiable assets open the release page instead.
Version 1.0.1 needs one manual upgrade to gain this updater.
Offline and rate-limited checks stay quiet.

Stickers now composite separately from effect artwork. Dark artwork in gameplay remains a known issue.

## Download and run

Download the Windows ZIP from [Releases](https://github.com/hypnomalice/reskate-deck-tool/releases),
extract it, and open **ReSkate Deck Tool.exe**. Python and the required libraries
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

### Custom deck shapes (SVG2Deck)

Deck graphics are drawn through the deck's board-space UVs: the underside is one
straight top-down 512 × 2048 tile. SVG2Deck builds shaped decks in that same tile,
so the exported graphic needs no changes; only artwork placement does.

1. Run SVG2Deck (2026-10-20a or newer). Its `Deck` folder gets
   `<name>_deck_shape.json` beside `<name>_underside_layout.png`.
2. Under **Deck shape**, choose **Load…** and pick the JSON. An
   `_underside_layout.png` works too, but it has no truck positions.
3. The preview, truck guides and thumbnail follow the outline.
   **Fit artwork to the shape** sizes and positions artwork inside the outline's
   bounds instead of the whole canvas. Turn it off for art that is already in board
   space (SVG2Deck's `Graphics Update` files, or art painted on the underside layout).
   **Extend edges past the outline** repeats edge pixels outward so parallax, depth
   and texture filtering never show the padding colour at the deck edge.
4. To check alignment in game, load `<name>_alignment_test_graphic.png` as a
   Lenticular deck's images with fitting turned off. Its white line should sit
   exactly on the deck edge.

**Standard** returns to the popsicle preview. Wood tint still uses the popsicle wood
texture. SVG2Deck keeps the popsicle UV0 regions, so the grain lines up, but a
tinted deck is expected to cover base art painted on your deck. Test it in game.

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

