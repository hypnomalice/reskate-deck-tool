# SDEC shared effect core

SDEC owns the common shader resources, empty graphic texture, bundle lookup and compositor script. Deck content contains artwork, masks, thumbnails, inventory items and private material recipes. The tool links to SDEC rather than exporting a duplicate core beside every deck.

The ABI remains version 1. Existing atlas markers and material identities are retained. The approved 1.2.0 core has 22 resources, including the native single-target emission variants used by Neon. Multi-picture lenticular extends the original 112-strip transition to 2–8 images.

`write_content_export` validates and partitions supported legacy content, then atomically writes only the requested FBMOD. It preserves original input packs. `split_pack` and the older diagnostic export API remain available for compatibility checks. These APIs do not change installed mods or load order.

## Compatibility limits

Shared program and compositor identities remain global. Central ownership prevents duplication among converted Deck Tool packs but cannot isolate unrelated mods that replace the same resources. Legacy packs with embedded shaders/scripts may need re-exporting or conversion. The current Luau plugin API does not provide material/shader/compositor control, so it cannot replace the compiled core.

The user verified the new 15-deck set in game. This is not a guarantee of compatibility with every third-party mod.
