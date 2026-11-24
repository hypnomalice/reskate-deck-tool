# SDEC shared effect core

Deck Tool 1.10.0 uses SDEC 3.5.0 or newer. SDEC owns shared shaders, compositor resources and motion controllers. Deck exports contain artwork, masks, thumbnails, inventory items, private material recipes and authored settings; there is no duplicate core or physics plugin per deck.

Shaker in Glass supports one to three independent PNG pieces with individual width, weight, collision shape and optional acrylic rims. Pieces share one shallow plane. The tool preview and SDEC execute the same solver source. Preview inspection controls do not become authored settings.

Existing effect identities and atlas contracts are preserved. SDEC 3.5.0 includes bounded shaker samples and clear-case mounting bores anchored to native mesh coordinates. Existing case decks receive that correction through the shared core.

Shared program and compositor identities remain global. Central ownership prevents duplicate cores among content-only Deck Tool packs; unrelated mods replacing the same resources can still conflict. Older packs with embedded scripts or shaders may need re-exporting or conversion. The Luau API updates declared material parameters; it does not compile or replace shared shaders.

The current Windows installation and all-effects pack passed the local combined mod audit. This is not a guarantee for every third-party mod, platform or multiplayer arrangement. SDEC remains a separate required installation.
