# Using Deck Tool 1.10.0

1. Install SDEC 3.5.0 or newer and keep one copy enabled first in ReSkate's mod list.
2. Extract the Windows tool ZIP and open ReSkate Deck Tool.exe.
3. Add a deck, choose its effect and select artwork. Save the project to keep settings and image paths.
4. Choose Mod ZIP, Install to game, or FBMOD. ZIP/direct installation asks for your game folder and a compatible Studio reskate_cli.exe on first use. The compiler must support `--board-loader-from-core` and is installed separately.
5. Import the ZIP with the launcher, or close the game/launcher and use direct installation. Enable the exported pack alongside SDEC.

For Shaker in Glass, choose a background and one to three PNG pieces. Set each piece's width, relative weight, collision shape and optional acrylic rim. Background blur and equipped grip tape are optional. PNG transparency defines an outline collision; a square image can use Rectangle. Pieces collide on one plane.

Use Shake preview to see movement, Pause to inspect a pose, Dim background to see clear rims, and Reset pieces to restart the simulation. These view controls do not alter the authored deck. Save/reload retains piece settings and the grip choice.

A deck ZIP contains native content and settings, not another copy of SDEC or a separate physics plugin. Share that ZIP with recipients who have the required core. They do not need the tool or compiler.

File > Convert older packs for SDEC creates content-only copies and preserves originals. Disable the older bundled versions after conversion to avoid duplicate shared effects. SDEC does not bypass the launcher's mod conflict rules.

Preview lighting, glass reflections and shape are approximate. Check authored decks in ReSkate before sharing. Transparent-deck FitCheck capture remains a known limitation.

## Per-layer holographic parallax (1.11.0)

In Effect > Parallax layer finishes, choose Normal or Holographic for each image layer. Strength is independent for every layer. Light artwork keeps dark backing normal; Whole layer coats all visible artwork; Mask PNG uses white, black and grey for full, zero and partial foil. The mask follows that layer’s placement. Use SDEC 3.6.0 or newer. See [the full guide](per-layer-holographic.md).
