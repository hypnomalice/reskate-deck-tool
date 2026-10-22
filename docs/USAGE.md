# ReSkate Deck Tool 1.4.0

Install one copy of [SDEC: Sofis Deck Effect Core](https://thunderstore.io/c/reskate/p/IdolRiot/Sofis_Deck_Effect_Core/), then import your exported deck FBMOD through Studio. Neon and multi-picture lenticular require SDEC 1.2.0 or newer. New exports contain deck artwork and settings only.

## Effects

- Animated / GIF: GIF, animated PNG or WebP. Up to 512 frames and 40.95 seconds; quality controls frame detail, not frame rate.
- Lenticular: choose 2–8 pictures. Reorder them with Move up / Move down. Fine lens bands and slight overlap are intentional.
- Depth Map: a colour image and grayscale depth map. White is near; black is far. Enable lenticular for stepped lens transitions.
- Parallax: transparent foreground and a complete background, plus an optional transparent middle layer with independent depth.
- Ghost Rare: depth-guided holographic sheen and silver shading.
- Metallic Flakes: angle-dependent sparkle on one graphic.
- Ink Flow: artwork plus a reveal mask. White receives the effect.
- Impossible Window: transparent front frame, background and optional object layer.
- Liquid Bottle: transparent front PNG, background, colour, cloudiness, depth, amount and visual thickness. Thickness changes ripples rather than simulating persistent viscosity.
- Neon: artwork plus a mask PNG. White glows, black does not; grey reduces glow and transparent pixels stay unlit. Or pick an artwork colour and adjust tolerance. Brightness 100% matches the approved Neon C test. Glow colour comes from the artwork.

Save a project to retain settings and picture order. Export one deck or all decks as an FBMOD. Custom thumbnails and wood tint remain available. The packaged examples contain 15 test decks covering all effects and key variants.

## Existing packs

Use File > Convert older packs for SDEC to create content-only copies, then disable their older bundled versions. Original files are preserved. Packs with their own shared scripts or shaders can still conflict; SDEC does not bypass the launcher's conflict rules.

## Preview

The preview illustrates atlas sampling before game lighting. Exposure, bloom, reflections, camera geometry and liquid movement can differ in game. Check wardrobe, gameplay and replay before sharing a new deck. Neon does not cast dynamic lights onto nearby objects.
