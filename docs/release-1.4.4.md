# ReSkate Deck Tool 1.4.4

Preview accuracy update, calibrated against 22 in-game deck captures.

- Standard-deck outline, tip curvature, artwork mapping and truck/bolt guides now better match the game-menu reference.
- Game room light applies a measured menu lighting profile. Turn it off for an unlit artwork view.
- Lenticular viewing direction, cross-deck curvature and image transitions are calibrated against two-, four- and eight-picture decks.
- Ink Flow and Impossible Window preview calculations now follow the authored shaders.
- Neon preserves artwork lighting separately from emission. Liquid Bottle uses gravity and a volume-conserving fill calculation when the board tilts.
- Exported-texture inspection can show compression in the preview. Preview preparation stays in the background.

The preview remains an approximation: native scene lighting, bloom, live liquid slosh and depth displacement can differ. The truck display is a placement guide, not the game's textured truck model.

107 tests pass, all 22 calibration projects render, and the packaged app passes its interface/export self-check. Existing exported artwork, approved shader resources and SDEC requirements are unchanged. SDEC core 1.3.0 is installed separately from Thunderstore; this update does not download or bundle the core, private PSDEC effects or a custom game DLL.
