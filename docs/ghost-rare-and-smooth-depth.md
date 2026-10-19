# Smooth effects

New projects start in Animated / GIF. The other choices are Lenticular,
Depth Map, Foreground / Background and Ghost Rare.

Depth Map and Foreground / Background use continuous motion by default.
Enable lenticular adds the lens-band variation; depth maps then use the existing
eight-view renderer. Projects saved before this option existed retain their
previous behaviour. Ghost Rare always uses continuous motion.

Ghost Rare takes colour artwork and a matching greyscale depth map. It combines
continuous inverse depth sampling, silver luminance shading, lower native
roughness and a rainbow sheen driven by local depth slopes. The preview models
the colour and depth calculations before game lighting; environment reflections
will differ in game.

Smooth depth uses the classic two-plane 512 x 4096 atlas: artwork in the first
plane and data in the second (red/blue coverage, green depth). Depth and settings
are sRGB-encoded so sampling returns linear data. The reserved header marker is
(64, 0, 255) for smooth depth or (128, 0, 255) for Ghost Rare. The next header
patch stores strength and convergence. All modes share the updated renderer,
including stickers and animation support.

In-game banding and shadow artefacts remain a separate renderer issue under
investigation. Ghost Rare was checked with stickers and Board Break during
prototype testing; app exports still need the usual in-game visual check.

Runtime check: the user confirmed Ghost Rare and smooth depth work with the app
export first and both prototype/probe mods disabled. Older enabled packs can
override the shared renderer; update them together or keep the new export first.
