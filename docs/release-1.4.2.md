# ReSkate Deck Tool 1.4.2

Ghost Rare now has separate **Silver area** and **Holo area** controls. Each can cover the whole board, use a mask PNG, or select an artwork colour with adjustable tolerance. White mask pixels apply the finish, black leaves the artwork, and grey or transparent pixels soften the coverage. Masks follow the artwork placement and depth movement.

Older projects default to whole-board finishes. Install the SDEC core supplied with this release to use selected finish areas in game; the previous core does not support independent silver and holo areas. No custom runtime DLL or experimental SDEC effects are included.

Automatic thumbnails now use the same standard-deck artwork mapping as the corrected preview. This removes the white nose/margin artifact when that margin lies outside the board's in-game artwork region. Custom thumbnail composition is unchanged.

Re-export and re-import older packs to replace embedded thumbnails or add finish areas. Source artwork, saved artwork positions, the reserved shader strip and the 2D/3D preview switch are preserved.
