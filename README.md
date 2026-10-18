# ReSkate Deck Tool - Beta

Make custom lenticular skateboard graphics for ReSkate. Export one deck or a workspace
of decks as an `.fbmod`, with custom names and thumbnails.

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
- Custom wood tint is preview-only; keep Original wood when exporting.
- Updates to the shared renderer across independently published mod versions need more testing.
- Projects reference image files rather than embedding them.

Board Break, classic flip, depth and multiple-deck exports have been tested on the
author's setup. Test your own artwork in the menu, gameplay and on a broken board.

## Run from source (Windows, Python 3.12)

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
It creates a classic/depth test pack and `build-check.json` with the result. This checks
archive structure, resource references and dependencies, not game compatibility.

## Licence and credits

App-owned source code is MIT licensed. See [LICENSE](LICENSE) and
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for dependencies and non-code assets.
This is an unofficial community tool, not affiliated with the game publisher.
