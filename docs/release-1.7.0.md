# Deck Tool 1.7.0 — Crystal and Artwork Springs

Crystal and Artwork Springs require SDEC 3.1.0 or newer. Keep one SDEC core enabled first. SDEC is installed separately from Thunderstore.

## Artwork Springs

Load the colour artwork, an optional grayscale depth map, and a jiggle mask. White mask pixels can move; black stays fixed. The mask and depth map follow the artwork placement. Set jiggle amount, stiffness, depth strength and attachment radius. Choose a top attachment, or top and bottom attachments to keep both ends fixed, then choose the fixed points on the artwork.

Drag the 3D board or press Tilt and release. The close-up enlarges the selected moving area. Stop moving ends the test movement while the springs continue to settle. The solver runs independently of rendering, with the same spring equations as SDEC. Game lighting and geometry can differ.

Settings are baked into each exported deck. SDEC handles movement in gameplay and the normal inventory preview; exported decks do not carry a separate motion plugin or in-game tuning page. Preview support requires ReSkate 2.1.4-5 Hotfix or newer (PR #467).

## Crystal

Choose embedded artwork, tint, cut density and whether to use the equipped grip. The exposed top and closed crystal shell retain native material bindings. Only cut crystal is exposed in this release.

## Fixes

- Correct the authored spring settings identifier so ReSkate accepts all three declared inputs.
- Observe the board before reading preview materials; SDEC includes the required read permission.
- Remove donor texture contributions from the jiggle material's normal, roughness, occlusion and colour outputs.
- Keep private shader resources marked as additions and preserve native grip slots across mesh LODs.
- Cache preview geometry and use a native renderer for spring artwork, while retaining the NumPy reference path for source development.

Validation includes cross-language spring traces, native/reference pixel comparisons, attachment and settings checks, Crystal grip checks, packaged digital-effects export and native compilation. In-game testing confirmed jiggle and removal of donor patterns in the normal preview on the official runtime. A fresh export from the final release still benefits from a visual check with your own artwork.

Artwork Springs supports **Mod ZIP** and **Install to game** exports, which include the authored movement settings. Bare FBMOD export remains available for the other effects.
