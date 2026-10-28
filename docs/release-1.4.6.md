# ReSkate Deck Tool 1.4.6

- Calibrated standard deck outline and truck/mounting guides from an in-game rotating calibration capture; applies to 2D and 3D previews.
- Sharper 2D artwork rendering and a thinner wood edge.
- Ink Flow: separate background and revealed ink colours, plus 0–100% graphic show-through.
- Ink Flow: reveal-mask strength, contrast and inversion, saved in projects and applied to previews and exports.
- Existing exported Ink decks keep their original behaviour with the updated core.

Custom Ink colours and graphic show-through require **SDEC core 1.4.0**, installed separately from Thunderstore, or the matching private PSDEC update. The tool does not download or install the core. Older cores ignore these new colour controls in game. Use one core only.

The standalone tool does not include private PSDEC effects, its plugin, the glass renderer or a custom game DLL. Existing export choices and artwork placement are retained.

Validation: 123 regression tests; packaged UI/export checks; all six Ink comparison decks passed the user's in-game test with PSDEC. Public and private shader variants validate; the private update changes exactly six shader asset records and preserves other resources. Preview shape remains calibrated to the standard donor deck rather than every custom mesh.
