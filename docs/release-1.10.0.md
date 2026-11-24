# Deck Tool 1.10.0

Requires **SDEC 3.5.0 or newer**, installed separately and enabled first. Deck recipients need the core and deck pack; the tool and compiler are only needed by authors.

The matching SDEC 3.5.0 ZIP accompanies the GitHub release for use while Thunderstore is being updated. Replace the existing core; keep one copy enabled.

- Adds Shaker in Glass with one to three independent PNG pieces, individual width and weight, and outline/rectangle/circle collisions on one plane.
- Adds optional acrylic rims with individual width and strength, optional internal background blur, and optional equipped grip tape.
- Adds an animated solver preview with shake, pause, reset and background dimming controls. Inspection controls stay out of saved deck settings.
- Preserves explicit grip-off settings during save/reload and export. Enabled grip uses the equipped design and stock top geometry.
- Uses finite artwork, rim and shadow coverage to avoid stretched rectangular acrylic samples.
- Skips incompatible legacy compilers during first-run automatic selection. ZIP/direct export still requires an external Studio compiler supporting shared-core board-loader inheritance.
- Includes standalone source-build instructions for both preview libraries and the exact MIT-licensed Luau source snapshot.

The accompanying SDEC 3.5.0 fixes clear-case mounting holes using native mesh coordinates and stock bolt positions. Existing frosted, glossy and circuit case decks receive the correction without re-exporting.

Existing effects and project formats are retained. Separate-plane shaker mode is not included. Preview lighting/geometry remain approximate. This release was checked on Windows x64; cross-platform and multiplayer display are not established. FitCheck capture of transparent decks remains a known limitation.
