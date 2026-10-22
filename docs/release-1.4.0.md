# 1.4.0

The new tool supports ordered 2–8 image lenticular decks with the original lens-strip transition, and native Neon using a PNG glow mask or colour selection with tolerance. Brightness 100% uses the approved Neon C setting.

Adds Metallic Flakes, Ink Flow, Impossible Window, Liquid Bottle and three-plane Parallax authoring alongside existing effects. Fixes the animation/depth selector overlap and resident texture headers. Previewing artwork while dragging now handles Neon and multi-picture decks too.

Exports contain deck content only. Install SDEC separately; Neon and multi-picture lenticular need SDEC 1.2.0 or newer. The tool links to the existing Thunderstore package. Original two-image projects remain supported.

Validation: 67 regression tests, all 15 effect/variant previews, project round trips and real FBMOD exports. The user confirmed the 15-deck pack in game. Native shader payloads match the approved set (24 surface and six emission pipeline checks). Previews remain illustrative; game exposure and bloom vary.
