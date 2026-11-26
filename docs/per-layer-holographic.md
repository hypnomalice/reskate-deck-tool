# Per-layer holographic parallax

Deck Tool 1.11.0 and SDEC 3.6.0 add donor Pearl holographic finishing to individual parallax layers. Both two-plane and three-plane exports were checked in ReSkate Dev.

Choose Foreground / Background. In the Effect tab, each visible layer has Normal or Holographic, strength, and an area choice. Light artwork leaves near-black backing unchanged. Whole layer coats the full visible PNG. Mask PNG uses white for the finish, black for ordinary artwork and grey for partial coverage. Mask placement follows that layer's artwork placement. Three-plane projects expose the middle layer independently.

The ordinary whole-board holographic overlay remains available for old projects. Selecting a per-layer holographic finish clears that overlay in the editor so a Normal flower is not recoloured by an additional global effect. Projects without layer_finishes export exactly their old artwork/alpha layout.

Export Mod ZIP or Install to game normally using the existing Studio compiler. Deck packs contain artwork and material routes, not another SDEC copy, Lua plugin or modified game DLL. Enable one matching SDEC core first. Players do not need the Deck Tool or Studio.

The preview uses the donor's palette and response under fixed approximate lighting; game foil pattern and reflections also depend on the game's global textures, normal maps and camera. It is not a game-lighting capture.

Authoring schema: layer_finishes maps foreground, middle and background to finish (normal/holographic), strength (0..1), area (light/all/mask), and mask (optional image path). Missing settings default to Normal. Three-plane PNG masks share one atlas channel at about 170 horizontal samples each; the artwork remains full width. Coverage alpha channels and ordinary shader output layouts are preserved.

Rebuilding the shader assets: runtime-source/layer-holographic/build.py --dxc <DXC folder> --assembler runtime-source/layer-holographic/assemble_dxil.py --output <empty packet folder>. baseline.zip holds the preserved shader inputs and donor Pearl kernel. The build validates DXIL and emits resources.tsv, payloads, metadata and a preservation report. It never changes a live game. Native SDEC packaging must preserve all existing resource identities, bundle placements and unrelated assets.

The export preserves both texel rows used by the shader recognition sample. The exporter validates that sample before creating a mod, including when the middle layer is Normal.
