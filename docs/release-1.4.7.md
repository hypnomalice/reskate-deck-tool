# ReSkate Deck Tool 1.4.7

Depth previews now use the same full-resolution depth views as exported decks, replacing the lighter approximate preview. Overlap, depth edges and hole filling match the export calculation.

- Smooth Depth and Ghost Rare follow the native shader displacement sequence.
- 3D depth, Smooth Depth and Ghost Rare use the calibrated viewing-angle response.
- 2D Game room light and neon emission preview follow the calibrated preview path.
- A tool-only native depth renderer speeds up generation, with pixel-identical Python fallback. On the development benchmark, one full-resolution view fell from 2.31 seconds to 0.020 seconds; results vary by hardware.

No SDEC update or custom game DLL is needed. The depth helper belongs to the tool only. No new PSDEC effects are included. Exported depth pixels remain unchanged. The preview remains an approximation of game lighting and compression; this is not the game renderer.
