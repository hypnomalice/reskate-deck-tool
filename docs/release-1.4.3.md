# ReSkate Deck Tool 1.4.3

Deck export now compresses texture strips in parallel at the existing quality setting. Large depth-map decks generate their eight views in parallel using the unchanged depth renderer. Both paths were checked against the old output byte for byte, including transparency, mipmaps and depth-view images.

Unchanged textures and depth views are reused during the same session, so repeating an export or changing only a name avoids repeating that work. The caches are bounded in memory (64 MiB for compressed textures and up to 32 MiB for one set of depth views); no persistent disk cache is added.

Effect previews render in the background with one frame in flight. Rapid changes replace pending work, old deck frames are rejected, and angle dragging uses a lighter preview before restoring full resolution on release. Export resolution and quality are unchanged.

On the representative test artwork, texture encoding took 4.2 seconds instead of 13.7 seconds, and eight depth views took 5.4 seconds instead of 19.8 seconds. Actual timings depend on hardware, source images and effect settings. Repeat-export cache hits refer to those stages, not the entire export.

SDEC core 1.3.0 remains a separate Thunderstore install. This update does not download, bundle or change the core, PSDEC, game runtime or shaders.
