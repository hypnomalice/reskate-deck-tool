# SDEC shared effect core

SDEC 3.1.0 adds Crystal and Artwork Springs. The shared spring controller lives in SDEC; native deck exports carry their three declared material inputs and authored settings. Preview updates require ReSkate 2.1.4-5 Hotfix or newer. The controller starts pose observation before material lookup and requires room, board, menu and skater.read permissions. No separate per-deck motion plugin is needed.

SDEC owns the common shader resources, empty graphic texture, bundle lookup and compositor script. Deck content contains artwork, masks, thumbnails, inventory items and private material recipes. The tool links to SDEC rather than exporting a duplicate core beside every deck.

The ABI remains version 1. Existing atlas markers and material identities are retained. The approved 1.2.0 core has 22 resources, including the native single-target emission variants used by Neon. Multi-picture lenticular extends the original 112-strip transition to 2–8 images.

`write_content_export` validates and partitions supported legacy content, then atomically writes only the requested FBMOD. It preserves original input packs. `split_pack` and the older diagnostic export API remain available for compatibility checks. These APIs do not change installed mods or load order.

## Compatibility limits

Shared program and compositor identities remain global. Central ownership prevents duplication among converted Deck Tool packs but cannot isolate unrelated mods that replace the same resources. Legacy packs with embedded shaders/scripts may need re-exporting or conversion. The Luau API can update declared parameters on an owned gameplay or preview material; it cannot replace or compile the shared shader and compositor resources.

The user verified the new 15-deck set in game. This is not a guarantee of compatibility with every third-party mod.
